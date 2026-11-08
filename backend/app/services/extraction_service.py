import logging
from typing import List, Dict, Any, Optional
from backend.app.config import settings
from backend.app.services.ai_service import default_ai_service, AIService
from backend.app.services.prompt_templates import EXTRACTION_SYSTEM_PROMPT

logger = logging.getLogger(__name__)

def extract_project_knowledge(
    chunk_text: str,
    page_number: int,
    filename: str,
    api_key: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Main extraction interface. Uses Gemini API if key is available, else uses deterministic engine.
    Returns list of finding dictionaries with entity_type, title, description, owner, deadline,
    task_status, priority, supporting_quotation, etc.
    """
    service = AIService(api_key=api_key) if api_key else default_ai_service
    items = service.extract_from_chunk(
        chunk_text=chunk_text,
        page_number=page_number,
        filename=filename
    )

    results = []
    for item in items:
        results.append({
            "entity_type": item.entity_type,
            "title": item.title,
            "description": item.description,
            "owner": item.owner,
            "deadline": item.deadline,
            "task_status": item.task_status,
            "priority": item.priority,
            "decided_by": item.decided_by,
            "decision_date": item.decision_date,
            "impact": item.impact,
            "likelihood": item.likelihood,
            "mitigation": item.mitigation,
            "related_entity": item.related_entity,
            "supporting_quotation": item.supporting_quotation,
            "confidence_score": item.confidence_score,
            "is_recommendation": item.is_recommendation,
            "page_number": item.page_number
        })
    return results

def extract_with_gemini(
    chunk_text: str,
    page_number: int,
    filename: str,
    api_key: str
) -> List[Dict[str, Any]]:
    return extract_project_knowledge(chunk_text, page_number, filename, api_key=api_key)

def extract_with_deterministic_engine(
    chunk_text: str,
    page_number: int,
    filename: str
) -> List[Dict[str, Any]]:
    service = AIService(api_key="")
    items = service._extract_deterministic(chunk_text, page_number, filename)
    return [item.model_dump() for item in items]
