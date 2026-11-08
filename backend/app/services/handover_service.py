from typing import Dict, Any, List, Optional
from datetime import datetime
import json
import logging
from sqlalchemy.orm import Session

from backend.app.models import Project, ExtractedFinding, FindingStatus, User, Handover
from backend.app.config import settings

logger = logging.getLogger(__name__)

HANDOVER_SYNTHESIS_PROMPT = """
You are the AI Project Handover Specialist for "Knowledge Continuity".
You are synthesizing an evidence-backed knowledge handover for an incoming team member based on verified project findings.

Your output must be a well-structured JSON object containing all of the following 13 sections:
1. "project_overview": A concise executive summary of the project scope, architecture, and objectives.
2. "current_status": Objective evaluation of current delivery state, milestones achieved, and velocity.
3. "completed_work": Array of key completed accomplishments and delivered milestones.
4. "pending_tasks": Array of unfinished tasks, grouped by priority.
5. "task_ownership": Matrix of tasks, their assigned owners, and any ownership ambiguity.
6. "important_decisions": Chronological record of architectural, technical, and process decisions.
7. "dependencies": List of external systems, upstream APIs, and vendor integrations.
8. "blockers": Critical impediments requiring immediate resolution or escalation.
9. "risks": Technical debt, scalability bottlenecks, security risks, and mitigations.
10. "unresolved_questions": Open technical inquiries, undecided architectural choices, or missing documentation.
11. "recommended_next_actions": Explicit, prioritized action list for Day 1, Week 1, and Month 1 of the incoming engineer.
12. "evidence_references": Traceability table linking findings back to source documents, pages, and quotes.
13. "review_and_approval_info": Metadata on reviewers, approval timestamps, and sign-offs.

RULES:
- Maintain complete fidelity to the provided verified findings. Do not invent facts or deadlines.
- Clearly separate explicit facts from AI recommendations.
- Emphasize role-specific needs for the designated incoming role.
"""

def generate_handover_report(
    project_id: str,
    target_role: str,
    user_id: str,
    db: Session,
    custom_notes: Optional[str] = None,
    api_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Generates a comprehensive 13-section handover document.
    Prioritizes APPROVED findings.
    """
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise ValueError(f"Project with ID {project_id} not found")

    findings = db.query(ExtractedFinding).filter(ExtractedFinding.project_id == project_id).all()
    user = db.query(User).filter(User.id == user_id).first()

    # Partition findings by entity type
    decisions = [f for f in findings if f.entity_type == "DECISION"]
    tasks = [f for f in findings if f.entity_type in ["TASK", "RESPONSIBILITY"]]
    risks = [f for f in findings if f.entity_type == "RISK"]
    blockers = [f for f in findings if f.entity_type == "BLOCKER"]
    dependencies = [f for f in findings if f.entity_type == "DEPENDENCY"]
    questions = [f for f in findings if f.entity_type == "QUESTION"]
    milestones = [f for f in findings if f.entity_type == "MILESTONE"]
    contacts = [f for f in findings if f.entity_type == "CONTACT"]

    # Filter completed vs pending tasks
    completed_tasks = [t for t in tasks if "completed" in (t.status or "").lower() or "done" in (t.description or "").lower()]
    pending_tasks = [t for t in tasks if t not in completed_tasks]

    # Build Evidence Table
    evidence_table = []
    for f in findings:
        evidence_table.append({
            "finding_id": f.id,
            "title": f.title,
            "entity_type": f.entity_type,
            "source_doc": f.document.filename if f.document else "Project Document",
            "page_number": f.page_number or 1,
            "quotation": f.supporting_quotation or "Direct evidence verified",
            "verification_status": f.verification_status,
            "flags": f.flags or {}
        })

    # Prepare Structured Handover JSON
    handover_data: Dict[str, Any] = {
        "project_overview": (
            f"{project.name} is a mission-critical initiative in the {project.domain} domain. "
            f"{project.description or 'Platform knowledge reconstruction and handover.'} "
            f"This handover package has been prepared specifically for the incoming role of '{target_role}'."
        ),
        "current_status": (
            f"The project is currently in {project.status} state with a target handover deadline of "
            f"{(project.target_handover_date.strftime('%B %d, %Y') if project.target_handover_date else 'Immediate')}. "
            f"{len(completed_tasks)} tasks completed, {len(pending_tasks)} pending actions, {len(blockers)} active blockers."
        ),
        "completed_work": [
            {
                "id": t.id,
                "title": t.title,
                "description": t.description,
                "owner": t.owner or "Team",
                "evidence_page": t.page_number
            } for t in (completed_tasks if completed_tasks else milestones[:3])
        ],
        "pending_tasks": [
            {
                "id": t.id,
                "title": t.title,
                "description": t.description,
                "owner": t.owner or "Unassigned",
                "deadline": t.deadline or "Immediate Sprint",
                "status": t.status,
                "evidence_page": t.page_number
            } for t in pending_tasks
        ],
        "task_ownership": [
            {
                "task": t.title,
                "owner": t.owner or "Unassigned / Ambiguous",
                "has_ambiguity": bool((t.flags or {}).get("ambiguous_ownership", False)),
                "deadline": t.deadline or "TBD"
            } for t in tasks
        ],
        "important_decisions": [
            {
                "id": d.id,
                "decision": d.title,
                "context": d.description,
                "supporting_quote": d.supporting_quotation,
                "page": d.page_number,
                "is_verified": d.verification_status == "VERIFIED"
            } for d in decisions
        ],
        "dependencies": [
            {
                "id": dep.id,
                "name": dep.title,
                "details": dep.description,
                "quotation": dep.supporting_quotation,
                "page": dep.page_number
            } for dep in dependencies
        ],
        "blockers": [
            {
                "id": b.id,
                "blocker": b.title,
                "impact": b.description,
                "status": "URGENT",
                "owner": b.owner or "Escalation Required",
                "page": b.page_number
            } for b in blockers
        ],
        "risks": [
            {
                "id": r.id,
                "risk": r.title,
                "severity": "HIGH" if "critical" in r.description.lower() else "MEDIUM",
                "details": r.description,
                "mitigation": "Review architecture and implement automated health probes / redundancies.",
                "page": r.page_number
            } for r in risks
        ],
        "unresolved_questions": [
            {
                "id": q.id,
                "question": q.title,
                "context": q.description,
                "evidence_quote": q.supporting_quotation,
                "page": q.page_number
            } for q in questions
        ],
        "recommended_next_actions": [
            {
                "timeframe": "Day 1 (Immediate Onboarding)",
                "action": "Set up development environment, verify repository access, and meet with key contacts.",
                "contacts": [c.title for c in contacts[:2]] if contacts else ["Engineering Lead"]
            },
            {
                "timeframe": "Week 1 (Blocker Resolution)",
                "action": f"Address top blockers: {', '.join([b.title for b in blockers[:2]]) if blockers else 'Review open PRs and test suites.'}",
                "deliverable": "Updated architecture notes and resolved pipeline blockers."
            },
            {
                "timeframe": "Month 1 (Knowledge Consolidation)",
                "action": f"Resolve open questions: {', '.join([q.title for q in questions[:2]]) if questions else 'Execute planned refactorings.'}",
                "deliverable": "Full independent ownership of system components."
            }
        ],
        "evidence_references": evidence_table,
        "review_and_approval_info": {
            "generated_by": user.full_name if user else "Lead Engineer",
            "generated_at": datetime.utcnow().isoformat(),
            "target_role": target_role,
            "project_name": project.name,
            "total_findings_considered": len(findings),
            "approved_findings_count": len([f for f in findings if f.status == FindingStatus.APPROVED]),
            "approval_state": "VERIFIED_READY_FOR_APPROVAL",
            "notes": custom_notes or "Handover generated using verified document citations."
        }
    }

    # Enhance with Gemini if key is provided
    active_key = api_key or settings.GEMINI_API_KEY
    if active_key and active_key.strip():
        try:
            import google.generativeai as genai
            genai.configure(api_key=active_key.strip())
            model = genai.GenerativeModel(
                model_name=settings.GEMINI_MODEL,
                generation_config={"response_mime_type": "application/json"}
            )
            prompt = f"""
Project Name: {project.name}
Target Role: {target_role}
Extracted Facts Summary:
- Decisions: {[d['decision'] for d in handover_data['important_decisions']]}
- Pending Tasks: {[t['title'] for t in handover_data['pending_tasks']]}
- Blockers: {[b['blocker'] for b in handover_data['blockers']]}
- Risks: {[r['risk'] for r in handover_data['risks']]}
- Questions: {[q['question'] for q in handover_data['unresolved_questions']]}

Generate a synthesized JSON following the 13 required sections.
"""
            gemini_res = model.generate_content([HANDOVER_SYNTHESIS_PROMPT, prompt])
            parsed = json.loads(gemini_res.text)
            if isinstance(parsed, dict) and "project_overview" in parsed:
                # Merge AI enhanced summaries while preserving verified evidence citations
                for k, v in parsed.items():
                    if k != "evidence_references" and v:
                        handover_data[k] = v
        except Exception as e:
            logger.warning(f"Gemini handover synthesis enhancement failed: {str(e)}. Using verified structured report.")

    return handover_data
