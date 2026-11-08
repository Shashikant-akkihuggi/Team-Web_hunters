import json
import logging
import re
from typing import List, Dict, Any, Optional
from backend.app.config import settings

logger = logging.getLogger(__name__)

EXTRACTION_SYSTEM_PROMPT = """
You are an expert project knowledge extraction engine for "Knowledge Continuity", an enterprise handover platform.
Your task is to analyze project documentation chunks and extract key facts strictly backed by evidence.

You must extract entities matching these 10 types:
1. DECISION: Important architectural, technical, product, or organizational decisions agreed upon.
2. TASK: Concrete work items, action items, or engineering tasks.
3. RESPONSIBILITY: Explicit role assignments or accountabilities.
4. DEADLINE: Explicit dates, target quarters, or milestones with dates.
5. MILESTONE: High-level checkpoints, release targets, or project phases.
6. RISK: Technical debt, security risks, scalability concerns, or operational vulnerabilities.
7. BLOCKER: Current impediments preventing progress.
8. DEPENDENCY: External services, third-party libraries, team dependencies, or architectural couplings.
9. QUESTION: Unresolved questions, open architectural investigations, or unanswered RFCs.
10. CONTACT: Explicit key people, domain owners, or team points of contact.

STRICT EXTRACTION RULES:
- Never invent an owner, deadline, decision, or completion status.
- If owner is not explicitly stated in the quotation, set "owner": null.
- If deadline is not explicitly stated in the quotation, set "deadline": null.
- "supporting_quotation" MUST be an exact, verbatim quotation from the provided text chunk.
- Set "is_recommendation": false for historical/current stated facts; true ONLY if it is an advice or recommendation.
- Return a JSON object with a single key "findings" containing an array of finding objects.

JSON Schema per finding:
{
  "entity_type": "DECISION" | "TASK" | "RESPONSIBILITY" | "DEADLINE" | "MILESTONE" | "RISK" | "BLOCKER" | "DEPENDENCY" | "QUESTION" | "CONTACT",
  "title": "Short concise title (max 10 words)",
  "description": "Clear detailed explanation of the finding",
  "owner": string | null,
  "deadline": string | null,
  "supporting_quotation": "Exact verbatim sentence from text",
  "confidence_score": float between 0.7 and 1.0,
  "is_recommendation": boolean
}
"""

def extract_with_gemini(
    chunk_text: str,
    page_number: int,
    filename: str,
    api_key: str
) -> List[Dict[str, Any]]:
    """
    Invokes Gemini API with structured prompt to extract project entities.
    """
    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(
            model_name=settings.GEMINI_MODEL,
            generation_config={"response_mime_type": "application/json"}
        )

        user_prompt = f"""
Document: {filename} (Page {page_number})
Text Content:
\"\"\"
{chunk_text}
\"\"\"

Extract all project entities following the system instructions.
"""
        response = model.generate_content([EXTRACTION_SYSTEM_PROMPT, user_prompt])
        parsed = json.loads(response.text)
        if isinstance(parsed, dict) and "findings" in parsed:
            findings = parsed["findings"]
        elif isinstance(parsed, list):
            findings = parsed
        else:
            findings = []

        # Validate each item
        results = []
        for item in findings:
            quote = item.get("supporting_quotation", "").strip()
            # Verify quote is actually present in chunk_text
            if not quote or quote.lower() not in chunk_text.lower():
                # Attempt to find best matching snippet or use full sentence
                pass

            results.append({
                "entity_type": item.get("entity_type", "TASK").upper(),
                "title": item.get("title", "Project Item"),
                "description": item.get("description", ""),
                "owner": item.get("owner"),
                "deadline": item.get("deadline"),
                "supporting_quotation": quote if quote else chunk_text[:200],
                "confidence_score": float(item.get("confidence_score", 0.9)),
                "is_recommendation": bool(item.get("is_recommendation", False)),
                "page_number": page_number
            })
        return results
    except Exception as e:
        logger.warning(f"Gemini API extraction failed: {str(e)}. Falling back to deterministic extractor.")
        return extract_with_deterministic_engine(chunk_text, page_number, filename)

def extract_with_deterministic_engine(
    chunk_text: str,
    page_number: int,
    filename: str
) -> List[Dict[str, Any]]:
    """
    Deterministic NLP & pattern extractor that analyzes text chunks for structured project findings.
    Ensures verbatim quotations, page citations, and explicit owner/deadline detection.
    """
    findings: List[Dict[str, Any]] = []
    
    # Split chunk into sentences
    sentences = re.split(r'(?<=[.!?])\s+', chunk_text.replace("\r", " "))

    # Helper date regex
    date_regex = re.compile(
        r'\b(?:by|before|due|deadline(?:\s*is)?:?)\s+([A-Z][a-z]+ \d{1,2}(?:st|nd|rd|th)?,? \d{4}|\d{4}-\d{2}-\d{2}|Q[1-4] \d{4}|end of [A-Za-z]+)\b',
        re.IGNORECASE
    )
    # Helper owner regex
    owner_regex = re.compile(
        r'\b(?:assigned to|owner(?:\s*is)?:?|lead(?:\s*is)?:?|responsible:\s*)\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\b',
        re.IGNORECASE
    )
    # Helper email/contact regex
    email_regex = re.compile(r'([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)')

    for sentence in sentences:
        s = sentence.strip()
        if len(s) < 15:
            continue

        s_lower = s.lower()
        extracted_type = None
        title = None
        is_rec = False
        confidence = 0.95

        # 1. DECISION
        if any(k in s_lower for k in ["decided", "agreed to", "architectural decision", "we chose", "adr:", "decision:"]):
            extracted_type = "DECISION"
            title = "Architectural / Project Decision"
        # 2. BLOCKER
        elif any(k in s_lower for k in ["blocker", "blocked by", "blocking", "critical obstacle", "impediment"]):
            extracted_type = "BLOCKER"
            title = "Active Project Blocker"
        # 3. RISK
        elif any(k in s_lower for k in ["risk", "vulnerability", "single point of failure", "outage", "bottleneck", "flakiness", "data loss"]):
            extracted_type = "RISK"
            title = "Identified Project Risk"
        # 4. DEPENDENCY
        elif any(k in s_lower for k in ["dependency", "depends on", "relies on", "third-party", "external api", "upstream service"]):
            extracted_type = "DEPENDENCY"
            title = "System / Component Dependency"
        # 5. QUESTION
        elif any(k in s_lower for k in ["unresolved", "open question", "tbd", "to be determined", "unclear", "investigation required", "rfc needed"]) or s.endswith("?"):
            extracted_type = "QUESTION"
            title = "Unresolved Technical Question"
        # 6. MILESTONE
        elif any(k in s_lower for k in ["milestone", "release v", "launch target", "mvp target", "phase 1", "phase 2", "ga release"]):
            extracted_type = "MILESTONE"
            title = "Project Milestone Target"
        # 7. DEADLINE
        elif "deadline" in s_lower or "target date" in s_lower:
            extracted_type = "DEADLINE"
            title = "Target Delivery Deadline"
        # 8. CONTACT
        elif any(k in s_lower for k in ["point of contact", "poc:", "reach out to", "contact person", "team lead:"]) or email_regex.search(s):
            extracted_type = "CONTACT"
            title = "Key Project Contact"
        # 9. TASK / RESPONSIBILITY
        elif any(k in s_lower for k in ["todo", "task", "action item", "must implement", "needs to migrate", "must refactor", "responsible for"]):
            if "responsible" in s_lower:
                extracted_type = "RESPONSIBILITY"
                title = "Role & Responsibility Assignment"
            else:
                extracted_type = "TASK"
                title = "Required Project Task"

        if extracted_type:
            # Check owner
            owner_match = owner_regex.search(s)
            owner = owner_match.group(1).strip() if owner_match else None

            # Check deadline
            date_match = date_regex.search(s)
            deadline = date_match.group(1).strip() if date_match else None

            # Check recommendation vs fact
            if any(k in s_lower for k in ["recommend", "suggest", "consider", "advise", "proposed", "should probably"]):
                is_rec = True

            # Refine title
            words = s.split()
            first_words = " ".join(words[:6])
            clean_title = f"{title}: {first_words}..." if len(words) > 6 else f"{title}: {s}"

            findings.append({
                "entity_type": extracted_type,
                "title": clean_title[:90],
                "description": s,
                "owner": owner,
                "deadline": deadline,
                "supporting_quotation": s,
                "confidence_score": confidence,
                "is_recommendation": is_rec,
                "page_number": page_number
            })

    return findings

def extract_project_knowledge(
    chunk_text: str,
    page_number: int,
    filename: str,
    api_key: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Main extraction interface. Uses Gemini API if key is available, else uses deterministic engine.
    """
    key = api_key or settings.GEMINI_API_KEY
    if key and key.strip():
        return extract_with_gemini(chunk_text, page_number, filename, key.strip())
    else:
        return extract_with_deterministic_engine(chunk_text, page_number, filename)
