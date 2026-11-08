import re
import logging
from datetime import datetime, date
from typing import Optional, Tuple, Dict, Any, List

logger = logging.getLogger(__name__)

MONTH_MAP = {
    'jan': 1, 'january': 1, 'feb': 2, 'february': 2, 'mar': 3, 'march': 3,
    'apr': 4, 'april': 4, 'may': 5, 'jun': 6, 'june': 6,
    'jul': 7, 'july': 7, 'aug': 8, 'august': 8, 'sep': 9, 'september': 9,
    'oct': 10, 'october': 10, 'nov': 11, 'november': 11, 'dec': 12, 'december': 12
}

def normalize_entity_type(raw_type: str) -> str:
    """Normalizes raw entity string into standardized EntityType."""
    if not raw_type:
        return "TASK"
    t = raw_type.strip().upper()
    valid_types = {
        "DECISION", "TASK", "RESPONSIBILITY", "DEADLINE", "MILESTONE",
        "RISK", "BLOCKER", "DEPENDENCY", "QUESTION", "CONTACT"
    }
    if t in valid_types:
        return t
    if "DECID" in t or "ADR" in t:
        return "DECISION"
    if "BLOCK" in t:
        return "BLOCKER"
    if "RISK" in t or "VULN" in t:
        return "RISK"
    if "DEPEND" in t or "PREREQ" in t:
        return "DEPENDENCY"
    if "QUEST" in t or "RFC" in t:
        return "QUESTION"
    if "MILESTONE" in t or "RELEASE" in t:
        return "MILESTONE"
    if "DEADLINE" in t or "DUE" in t:
        return "DEADLINE"
    if "RESPONSIB" in t or "ROLE" in t:
        return "RESPONSIBILITY"
    return "TASK"

def normalize_task_status(raw_status: Optional[str], raw_text: Optional[str] = None) -> str:
    """
    Normalizes task status into one of:
    - NOT_STARTED
    - IN_PROGRESS
    - BLOCKED
    - COMPLETED
    - UNKNOWN

    Strictly preserves UNKNOWN if evidence is ambiguous or missing.
    Never assumes completed without explicit evidence.
    """
    candidates = []
    if raw_status:
        candidates.append(raw_status.strip().upper())
    if raw_text:
        candidates.append(raw_text.strip().lower())

    combined = " ".join(candidates)

    if any(k in combined for k in ["completed", "complete", "done", "finished", "shipped", "is complete"]):
        return "COMPLETED"
    if any(k in combined for k in ["blocked", "blocking", "impeded", "blocked pending"]):
        return "BLOCKED"
    if any(k in combined for k in ["in_progress", "in progress", "wip", "underway", "currently working", "assigned to"]):
        return "IN_PROGRESS"
    if any(k in combined for k in ["not_started", "not started", "pending", "todo", "to do", "planned"]):
        return "NOT_STARTED"

    return "UNKNOWN"

def parse_normalized_date(date_str: Optional[str]) -> Tuple[Optional[str], Optional[date]]:
    """
    Parses a raw date string into ISO 'YYYY-MM-DD' or 'YYYY-Q#' format.
    Returns (iso_string, datetime.date_object).
    If date cannot be resolved or is absent, returns (None, None).
    NEVER invents dates.
    """
    if not date_str or not date_str.strip():
        return None, None

    s = date_str.strip()

    # 1. Standard ISO YYYY-MM-DD
    iso_match = re.search(r'\b(20\d{2})[-/](0[1-9]|1[0-2])[-/](0[1-9]|[12]\d|3[01])\b', s)
    if iso_match:
        y, m, d = int(iso_match.group(1)), int(iso_match.group(2)), int(iso_match.group(3))
        try:
            parsed = date(y, m, d)
            return parsed.isoformat(), parsed
        except ValueError:
            pass

    # 2. Month DD, YYYY or DD Month YYYY (e.g. October 1, 2026 or 15 Dec 2026)
    m_name_match = re.search(r'\b([A-Za-z]+)\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(20\d{2})\b', s)
    if m_name_match:
        month_name = m_name_match.group(1).lower()
        d_val = int(m_name_match.group(2))
        y_val = int(m_name_match.group(3))
        if month_name in MONTH_MAP:
            try:
                parsed = date(y_val, MONTH_MAP[month_name], d_val)
                return parsed.isoformat(), parsed
            except ValueError:
                pass

    d_name_match = re.search(r'\b(\d{1,2})(?:st|nd|rd|th)?\s+([A-Za-z]+),?\s+(20\d{2})\b', s)
    if d_name_match:
        d_val = int(d_name_match.group(1))
        month_name = d_name_match.group(2).lower()
        y_val = int(d_name_match.group(3))
        if month_name in MONTH_MAP:
            try:
                parsed = date(y_val, MONTH_MAP[month_name], d_val)
                return parsed.isoformat(), parsed
            except ValueError:
                pass

    # 3. Quarter format: Q1 2026, Q4-2026
    q_match = re.search(r'\b(Q[1-4])[-/\s]+(20\d{2})\b', s, re.IGNORECASE)
    if q_match:
        return f"{q_match.group(2)}-{q_match.group(1).upper()}", None

    # 4. Month YYYY (e.g. end of October 2026)
    my_match = re.search(r'\b([A-Za-z]+)\s+(20\d{2})\b', s)
    if my_match:
        month_name = my_match.group(1).lower()
        y_val = int(my_match.group(2))
        if month_name in MONTH_MAP:
            return f"{y_val}-{MONTH_MAP[month_name]:02d}", None

    return None, None

def check_is_overdue(deadline_date: Optional[date], task_status: str, reference_date: Optional[date] = None) -> bool:
    """
    Checks if a task is overdue.
    Only returns True if a valid deadline date exists, task_status != COMPLETED, and deadline < reference_date.
    Never infers overdue without a valid deadline.
    """
    if not deadline_date or task_status.upper() == "COMPLETED":
        return False
    ref = reference_date or date.today()
    return deadline_date < ref

def clean_core_topic(text: str) -> str:
    """Strips common prefix labels like 'Task:', 'Decision:', 'Blocked Task:' and collapses whitespace."""
    if not text:
        return ""
    clean = re.sub(r'^(?:task|decision|risk|blocker|dependency|question|milestone|blocked task):\s*', '', text, flags=re.IGNORECASE)
    return re.sub(r'\s+', ' ', clean).strip().lower()

def resolve_entity_links(target_name: str, available_entities: List[Dict[str, Any]]) -> List[str]:
    """
    Finds matching entity IDs for a dependency target name.
    """
    norm_target = clean_core_topic(target_name)
    matches = []
    for ent in available_entities:
        ent_title = clean_core_topic(ent.get("title", ""))
        ent_desc = clean_core_topic(ent.get("description", ""))
        if norm_target in ent_title or ent_title in norm_target or (len(norm_target) > 5 and norm_target in ent_desc):
            matches.append(ent["id"])
    return matches
