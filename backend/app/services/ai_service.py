import json
import logging
import re
import time
from typing import List, Dict, Any, Optional
from backend.app.config import settings
from backend.app.schemas import ExtractedEntityItem, ExtractedEntitiesPayload
from backend.app.services.prompt_templates import (
    EXTRACTION_SYSTEM_PROMPT,
    EXTRACTION_USER_PROMPT_TEMPLATE
)

logger = logging.getLogger(__name__)

# Common regex patterns for deterministic parsing
DATE_PATTERN = re.compile(
    r'\b(?:by|before|due|deadline(?:\s*is)?:?)\s+([A-Z][a-z]+ \d{1,2}(?:st|nd|rd|th)?,? \d{4}|\d{4}-\d{2}-\d{2}|Q[1-4] \d{4}|end of [A-Za-z]+|\d{1,2}/\d{1,2}/\d{2,4})\b',
    re.IGNORECASE
)
OWNER_PATTERN = re.compile(
    r'\b(?:assigned to|owner(?:\s*is)?:?|lead(?:\s*is)?:?|responsible:\s*)\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\b',
    re.IGNORECASE
)
EMAIL_PATTERN = re.compile(r'([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)')


class AIService:
    """
    Dedicated AI extraction service supporting Gemini API with automatic fallback
    to deterministic zero-hallucination NLP parsing.
    """

    def __init__(self, api_key: Optional[str] = None, model_name: Optional[str] = None):
        self.api_key = (api_key or settings.GEMINI_API_KEY or "").strip()
        self.model_name = model_name or settings.GEMINI_MODEL or "gemini-1.5-flash"
        self._genai_client = None

        if self.api_key:
            try:
                import google.generativeai as genai
                genai.configure(api_key=self.api_key)
                self._genai_client = genai.GenerativeModel(
                    model_name=self.model_name,
                    generation_config={"response_mime_type": "application/json"}
                )
                logger.info(f"Gemini AI Service initialized with model: {self.model_name}")
            except Exception as e:
                logger.warning(f"Failed to configure Gemini client: {e}. Will use deterministic fallback.")
                self._genai_client = None

    @property
    def is_gemini_active(self) -> bool:
        return self._genai_client is not None

    def extract_from_chunk(
        self,
        chunk_text: str,
        page_number: int = 1,
        filename: str = "Document",
        chunk_index: int = 0
    ) -> List[ExtractedEntityItem]:
        """
        Extracts structured findings from chunk text. Uses Gemini if active; falls back to deterministic.
        Validates quotes against chunk text.
        """
        if not chunk_text or not chunk_text.strip():
            return []

        if self.is_gemini_active:
            try:
                results = self._extract_with_gemini(chunk_text, page_number, filename, chunk_index)
                if results:
                    return results
            except Exception as err:
                logger.warning(f"Gemini extraction error: {err}. Falling back to deterministic NLP.")

        return self._extract_deterministic(chunk_text, page_number, filename)

    def _extract_with_gemini(
        self,
        chunk_text: str,
        page_number: int,
        filename: str,
        chunk_index: int
    ) -> List[ExtractedEntityItem]:
        """
        Invokes Gemini API with retry logic and Pydantic validation.
        """
        prompt = EXTRACTION_USER_PROMPT_TEMPLATE.format(
            filename=filename,
            page_number=page_number,
            chunk_index=chunk_index,
            chunk_text=chunk_text
        )

        max_retries = 3
        backoff = 1.0

        for attempt in range(max_retries):
            try:
                response = self._genai_client.generate_content([EXTRACTION_SYSTEM_PROMPT, prompt])
                raw_text = response.text.strip()
                parsed = json.loads(raw_text)

                raw_findings = []
                if isinstance(parsed, dict) and "findings" in parsed:
                    raw_findings = parsed["findings"]
                elif isinstance(parsed, list):
                    raw_findings = parsed

                items: List[ExtractedEntityItem] = []
                for rf in raw_findings:
                    # Sanitize and validate quotation
                    quote = rf.get("supporting_quotation", "").strip()
                    if not quote or quote.lower() not in chunk_text.lower():
                        # Find closest sentence or reject hallucinated quote
                        quote = self._find_best_quotation(rf.get("title", ""), chunk_text) or chunk_text[:200]

                    item = ExtractedEntityItem(
                        entity_type=rf.get("entity_type", "TASK").upper(),
                        title=rf.get("title", "Project Item").strip()[:255],
                        description=rf.get("description", "").strip(),
                        owner=rf.get("owner") or None,
                        deadline=rf.get("deadline") or None,
                        task_status=rf.get("task_status") or None,
                        priority=rf.get("priority") or None,
                        decided_by=rf.get("decided_by") or None,
                        decision_date=rf.get("decision_date") or None,
                        impact=rf.get("impact") or None,
                        likelihood=rf.get("likelihood") or None,
                        mitigation=rf.get("mitigation") or None,
                        related_entity=rf.get("related_entity") or None,
                        supporting_quotation=quote,
                        confidence_score=float(rf.get("confidence_score", 0.9)),
                        is_recommendation=bool(rf.get("is_recommendation", False)),
                        page_number=page_number
                    )
                    items.append(item)

                return items
            except Exception as e:
                logger.warning(f"Gemini API attempt {attempt+1} failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(backoff)
                    backoff *= 2
                else:
                    raise e

        return []

    def _extract_deterministic(
        self,
        chunk_text: str,
        page_number: int,
        filename: str
    ) -> List[ExtractedEntityItem]:
        """
        Deterministic NLP extractor:
        - Splits chunk into sentences.
        - Identifies decisions, tasks (with status), risks, blockers, dependencies, questions, etc.
        - Preserves exact verbatim quotations.
        - Detects task status: COMPLETED, IN_PROGRESS, BLOCKED, NOT_STARTED.
        """
        findings: List[ExtractedEntityItem] = []
        sentences = re.split(r'(?<=[.!?])\s+', chunk_text.replace("\r", " "))

        for sentence in sentences:
            s = sentence.strip()
            if len(s) < 15:
                continue

            s_lower = s.lower()
            extracted_type: Optional[str] = None
            title: Optional[str] = None
            task_status: Optional[str] = None
            priority: Optional[str] = None
            decided_by: Optional[str] = None
            related_entity: Optional[str] = None
            is_rec = False
            confidence = 0.95

            # 1. DECISION
            if any(k in s_lower for k in [
                "decided to", "we decided", "decision:", "agreed to", "architectural decision",
                "we chose", "adr:", "chosen for", "selected for"
            ]):
                extracted_type = "DECISION"
                # Extract subject
                m = re.search(r'(?:decided to|decision:|we chose|agreed to)\s+([^,.;]+)', s, re.IGNORECASE)
                subject = m.group(1).strip() if m else s[:40]
                title = f"Decision: {subject}"[:90]

            # 2. BLOCKER / BLOCKED TASK
            elif any(k in s_lower for k in ["blocker", "blocked by", "blocking", "critical obstacle", "impediment", "is blocked"]):
                # Determine if it's a blocked task or a standalone blocker
                if "task" in s_lower or "integration" in s_lower or "pipeline" in s_lower or "service" in s_lower:
                    extracted_type = "TASK"
                    task_status = "BLOCKED"
                    priority = "HIGH"
                    title = self._clean_task_title(s, "Blocked Task")
                else:
                    extracted_type = "BLOCKER"
                    priority = "CRITICAL"
                    title = f"Blocker: {s[:50]}..."

            # 3. TASK / WORK ITEM / ACTION ITEM (Check before pure DEADLINE)
            elif any(k in s_lower for k in [
                "assigned to", "todo", "task", "action item", "must implement", "needs to",
                "completed", "in progress", "responsible for", "integration is"
            ]):
                if "responsible for" in s_lower and "assigned" not in s_lower and "task" not in s_lower:
                    extracted_type = "RESPONSIBILITY"
                    title = f"Responsibility: {s[:50]}..."
                else:
                    extracted_type = "TASK"
                    # Determine task status
                    if any(w in s_lower for w in ["completed", "done", "finished", "is complete", "shipped"]):
                        task_status = "COMPLETED"
                    elif any(w in s_lower for w in ["blocked", "blocking", "impeded"]):
                        task_status = "BLOCKED"
                    elif any(w in s_lower for w in ["pending", "todo", "not started", "planned", "to do"]):
                        task_status = "NOT_STARTED"
                    elif any(w in s_lower for w in ["in progress", "wip", "currently working", "underway", "assigned to"]):
                        task_status = "IN_PROGRESS"
                    else:
                        task_status = "IN_PROGRESS"

                    title = self._clean_task_title(s, "Task")

            # 4. DEPENDENCY
            elif any(k in s_lower for k in ["depends on", "dependency", "relies on", "prerequisite", "upstream service", "external api"]):
                extracted_type = "DEPENDENCY"
                m = re.search(r'(?:depends on|relies on|prerequisite is|dependency:?)\s+([^,.;]+)', s, re.IGNORECASE)
                if m:
                    related_entity = m.group(1).strip()
                title = f"Dependency: {related_entity or s[:40]}"[:90]

            # 5. RISK
            elif any(k in s_lower for k in ["risk", "vulnerability", "single point of failure", "outage", "bottleneck", "flakiness", "data loss"]):
                extracted_type = "RISK"
                priority = "HIGH" if any(w in s_lower for w in ["critical", "data loss", "high", "severe"]) else "MEDIUM"
                title = f"Risk: {s[:50]}..."

            # 6. QUESTION / UNRESOLVED
            elif any(k in s_lower for k in ["unresolved", "open question", "tbd", "to be determined", "unclear", "investigation required", "rfc needed"]) or s.endswith("?"):
                extracted_type = "QUESTION"
                title = f"Open Question: {s[:50]}..."

            # 7. MILESTONE
            elif any(k in s_lower for k in ["milestone", "release v", "launch target", "mvp target", "phase 1", "phase 2", "ga release"]):
                extracted_type = "MILESTONE"
                title = f"Milestone: {s[:50]}..."

            # 8. DEADLINE
            elif "deadline" in s_lower or "target delivery" in s_lower:
                extracted_type = "DEADLINE"
                title = f"Target Deadline: {s[:50]}..."

            # 9. CONTACT
            elif any(k in s_lower for k in ["point of contact", "poc:", "reach out to", "contact person", "team lead:"]) or EMAIL_PATTERN.search(s):
                extracted_type = "CONTACT"
                title = f"Contact: {s[:50]}..."

            if extracted_type:
                # Detect owner
                owner_match = OWNER_PATTERN.search(s)
                if owner_match:
                    raw_owner = owner_match.group(1).strip()
                    owner = re.split(r'\s+(?:with|before|due|by|on|for|at|and)\b', raw_owner, flags=re.IGNORECASE)[0].strip()
                else:
                    owner = None

                # Detect deadline
                date_match = DATE_PATTERN.search(s)
                deadline = date_match.group(1).strip() if date_match else None

                # Detect recommendation vs fact
                if any(k in s_lower for k in ["recommend", "suggest", "consider", "advise", "proposed", "should probably"]):
                    is_rec = True

                item = ExtractedEntityItem(
                    entity_type=extracted_type,
                    title=title or f"{extracted_type}: {s[:40]}",
                    description=s,
                    owner=owner,
                    deadline=deadline,
                    task_status=task_status,
                    priority=priority or "MEDIUM",
                    decided_by=decided_by,
                    related_entity=related_entity,
                    supporting_quotation=s,
                    confidence_score=confidence,
                    is_recommendation=is_rec,
                    page_number=page_number
                )
                findings.append(item)

        return findings

    def _clean_task_title(self, sentence: str, default_prefix: str) -> str:
        """Derives a clean title from a sentence describing a task."""
        # e.g. "Payment integration is assigned to Rahul with deadline 2026-12-15" -> "Payment integration"
        # e.g. "Authentication service is completed" -> "Authentication service"
        m = re.match(r'^\s*([A-Za-z0-9\s_-]+?)\s+(?:is|has been|was|must be|assigned to)\b', sentence, re.IGNORECASE)
        if m and len(m.group(1).strip().split()) <= 6:
            return m.group(1).strip().title()
        words = sentence.split()
        return f"{default_prefix}: {' '.join(words[:5])}..." if len(words) > 5 else sentence

    def _find_best_quotation(self, query: str, text: str) -> Optional[str]:
        """Finds matching sentence in text for a query title."""
        sentences = re.split(r'(?<=[.!?])\s+', text)
        q_words = set(query.lower().split())
        best_sentence = None
        best_score = 0
        for s in sentences:
            s_words = set(s.lower().split())
            if not s_words:
                continue
            overlap = len(q_words.intersection(s_words))
            if overlap > best_score:
                best_score = overlap
                best_sentence = s.strip()
        return best_sentence


# Module-level default service instance
default_ai_service = AIService()
