import logging
from datetime import datetime, date
from typing import Optional, Dict, Any, List, Set, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import or_

from backend.app.models import (
    Project, ProjectMember, Document, DocumentChunk, ExtractedFinding,
    EvidenceReference, KnowledgeConflict, ProjectReconstruction,
    VerificationStatus, User
)
from backend.app.schemas import (
    ProjectStateResponse, ProjectOverviewState, ProjectOwnershipState,
    ProjectUncertaintyState, DecisionTimelineResponse, DecisionTimelineEvent,
    TaskTimelineResponse, TaskTimelineItem, DependencyGraphResponse,
    DependencyGraphNode, DependencyGraphEdge, ResponsibilitiesResponse,
    OwnerResponsibilityItem, RiskRegisterResponse, RiskRegisterItem,
    KnowledgeSearchResponse, KnowledgeSearchItem
)
from backend.app.services.knowledge_normalization_service import (
    normalize_entity_type, normalize_task_status, parse_normalized_date,
    check_is_overdue, clean_core_topic, resolve_entity_links
)

logger = logging.getLogger(__name__)

def reconstruct_project_state(
    project_id: str,
    db: Session,
    user_id: Optional[str] = None,
    force: bool = False
) -> ProjectStateResponse:
    """
    Synthesizes the complete current project state from extracted database findings.
    Calculates overview, task status distribution, ownership mapping, uncertainty metrics,
    and records a persistent ProjectReconstruction snapshot.
    """
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise ValueError(f"Project {project_id} not found")

    findings = db.query(ExtractedFinding).filter(ExtractedFinding.project_id == project_id).all()
    conflicts = db.query(KnowledgeConflict).filter(KnowledgeConflict.project_id == project_id).all()
    members = db.query(ProjectMember).filter(ProjectMember.project_id == project_id).all()
    docs = db.query(Document).filter(Document.project_id == project_id).all()

    # 1. Task State Breakdown
    tasks = [f for f in findings if f.entity_type == "TASK"]
    completed_tasks = 0
    in_progress_tasks = 0
    blocked_tasks = 0
    not_started_tasks = 0
    unknown_tasks = 0

    missing_deadlines = 0
    unknown_ownership = 0
    distinct_owners: Set[str] = set()
    ambiguous_owners = 0

    for t in tasks:
        st = normalize_task_status(t.task_status, t.description or t.supporting_quotation)
        if st == "COMPLETED":
            completed_tasks += 1
        elif st == "BLOCKED":
            blocked_tasks += 1
        elif st == "IN_PROGRESS":
            in_progress_tasks += 1
        elif st == "NOT_STARTED":
            not_started_tasks += 1
        else:
            unknown_tasks += 1

        # Check deadline
        if not t.deadline or not t.deadline.strip():
            missing_deadlines += 1

        # Check owner
        if not t.owner or not t.owner.strip():
            unknown_ownership += 1
        else:
            cleaned_owner = t.owner.strip()
            distinct_owners.add(cleaned_owner)
            if any(k in cleaned_owner.lower() for k in [" or ", "unclear", "tbd", "team"]):
                ambiguous_owners += 1

    total_tasks_count = len(tasks)
    known_status_tasks = completed_tasks + in_progress_tasks + blocked_tasks + not_started_tasks
    completion_rate = round((completed_tasks / known_status_tasks * 100), 1) if known_status_tasks > 0 else 0.0

    # 2. Decisions, Risks, Questions, Dependencies
    decisions = [f for f in findings if f.entity_type == "DECISION"]
    risks = [f for f in findings if f.entity_type == "RISK"]
    blockers = [f for f in findings if f.entity_type == "BLOCKER"]
    questions = [f for f in findings if f.entity_type == "QUESTION"]
    dependencies = [f for f in findings if f.entity_type == "DEPENDENCY"]

    # 3. Uncertainty & Anomaly Calculation
    unsupported_count = sum(1 for f in findings if f.verification_status == VerificationStatus.UNSUPPORTED)
    ownership_conflicts_count = sum(1 for c in conflicts if c.conflict_type == "OWNERSHIP")
    conflicting_statuses_count = sum(1 for c in conflicts if c.conflict_type == "STATUS")

    overview = ProjectOverviewState(
        total_tasks=total_tasks_count,
        completed_tasks=completed_tasks,
        in_progress_tasks=in_progress_tasks,
        blocked_tasks=blocked_tasks,
        not_started_tasks=not_started_tasks,
        unknown_status_tasks=unknown_tasks,
        completion_rate=completion_rate,
        total_decisions=len(decisions),
        open_risks=len(risks) + len(blockers),
        unresolved_questions=len(questions),
        total_dependencies=len(dependencies)
    )

    ownership_state = ProjectOwnershipState(
        assigned_tasks_count=total_tasks_count - unknown_ownership,
        unassigned_tasks_count=unknown_ownership,
        distinct_owners_count=len(distinct_owners),
        ambiguous_owners_count=ambiguous_owners,
        ownership_conflicts_count=ownership_conflicts_count
    )

    uncertainty_state = ProjectUncertaintyState(
        missing_deadlines_count=missing_deadlines,
        unknown_ownership_count=unknown_ownership,
        conflicting_statuses_count=conflicting_statuses_count,
        unsupported_claims_count=unsupported_count
    )

    # 4. Data Freshness Determination
    latest_doc_time = max(
        (d.created_at for d in docs if d.created_at),
        default=project.created_at
    )
    is_fresh = True
    if project.last_reconstructed_at:
        is_fresh = (project.last_reconstructed_at >= latest_doc_time)
    freshness_status = "UP_TO_DATE" if is_fresh else "STALE"

    # Summaries for overview cards
    active_blockers_summary = [
        {
            "id": b.id,
            "title": b.title,
            "description": b.description,
            "supporting_quotation": b.supporting_quotation,
            "page_number": b.page_number
        } for b in (blockers + [t for t in tasks if normalize_task_status(t.task_status, t.description) == "BLOCKED"])[:5]
    ]

    recent_decisions_summary = [
        {
            "id": d.id,
            "title": d.title,
            "description": d.description,
            "decision_date": d.decision_date,
            "decided_by": d.decided_by,
            "page_number": d.page_number
        } for d in decisions[:5]
    ]

    # 5. Persist Snapshot in ProjectReconstruction
    new_version = (project.reconstruction_version or 0) + 1
    reconstruction = ProjectReconstruction(
        project_id=project_id,
        version=new_version,
        overview_json=overview.model_dump(),
        risk_register_json={
            "risks_count": len(risks),
            "blockers_count": len(blockers)
        },
        responsibilities_json={
            "distinct_owners": list(distinct_owners),
            "unassigned_tasks": unknown_ownership
        },
        freshness_status=freshness_status,
        reconstructed_by=user_id
    )
    db.add(reconstruction)

    project.last_reconstructed_at = datetime.utcnow()
    project.reconstruction_version = new_version
    db.commit()

    return ProjectStateResponse(
        project_id=project.id,
        project_name=project.name,
        project_description=project.description,
        project_status=project.status,
        last_reconstructed_at=project.last_reconstructed_at,
        version=new_version,
        freshness_status=freshness_status,
        overview=overview,
        ownership_state=ownership_state,
        uncertainty_state=uncertainty_state,
        active_blockers_summary=active_blockers_summary,
        recent_decisions_summary=recent_decisions_summary
    )

def get_decision_timeline(
    project_id: str,
    db: Session,
    search: Optional[str] = None
) -> DecisionTimelineResponse:
    """
    Constructs a chronological timeline of project decisions.
    Separates dated decisions from undated decisions.
    Never invents decision dates.
    """
    query = db.query(ExtractedFinding).filter(
        ExtractedFinding.project_id == project_id,
        ExtractedFinding.entity_type == "DECISION"
    )
    if search:
        query = query.filter(
            or_(
                ExtractedFinding.title.ilike(f"%{search}%"),
                ExtractedFinding.description.ilike(f"%{search}%"),
                ExtractedFinding.supporting_quotation.ilike(f"%{search}%")
            )
        )
    decisions = query.all()

    dated_events: List[DecisionTimelineEvent] = []
    undated_events: List[DecisionTimelineEvent] = []

    for d in decisions:
        doc = db.query(Document).filter(Document.id == d.document_id).first() if d.document_id else None
        iso_date, date_obj = parse_normalized_date(d.decision_date or d.deadline)

        event = DecisionTimelineEvent(
            id=d.id,
            project_id=d.project_id,
            title=d.title,
            description=d.description,
            decision_date=d.decision_date or d.deadline,
            normalized_date=iso_date,
            has_date=bool(iso_date),
            decided_by=d.decided_by or d.owner,
            source_document=doc.filename if doc else None,
            document_id=d.document_id,
            supporting_quotation=d.supporting_quotation,
            page_number=d.page_number or 1,
            verification_status=d.verification_status,
            confidence_score=d.confidence_score or 1.0,
            flags=d.flags or {},
            created_at=d.created_at
        )

        if iso_date:
            dated_events.append(event)
        else:
            undated_events.append(event)

    # Sort dated events chronologically (earliest to latest or latest to earliest)
    dated_events.sort(key=lambda e: e.normalized_date or "", reverse=True)

    return DecisionTimelineResponse(
        dated_events=dated_events,
        undated_events=undated_events,
        total_decisions=len(decisions)
    )

def get_task_timeline(
    project_id: str,
    db: Session,
    status_filter: Optional[str] = None,
    owner_filter: Optional[str] = None
) -> TaskTimelineResponse:
    """
    Builds chronological project task schedule with overdue detection
    and dependency associations.
    """
    query = db.query(ExtractedFinding).filter(
        ExtractedFinding.project_id == project_id,
        ExtractedFinding.entity_type == "TASK"
    )
    if owner_filter:
        query = query.filter(ExtractedFinding.owner.ilike(f"%{owner_filter}%"))
    
    tasks = query.all()

    # Pre-fetch dependencies
    deps = db.query(ExtractedFinding).filter(
        ExtractedFinding.project_id == project_id,
        ExtractedFinding.entity_type == "DEPENDENCY"
    ).all()

    timeline_items: List[TaskTimelineItem] = []
    completed_count = 0
    in_progress_count = 0
    blocked_count = 0
    overdue_count = 0
    unassigned_count = 0

    today = date.today()

    for t in tasks:
        doc = db.query(Document).filter(Document.id == t.document_id).first() if t.document_id else None
        st = normalize_task_status(t.task_status, t.description or t.supporting_quotation)
        
        if status_filter and status_filter.upper() != "ALL":
            if st != status_filter.upper():
                continue

        iso_deadline, deadline_obj = parse_normalized_date(t.deadline)
        is_overdue = check_is_overdue(deadline_obj, st, today)

        if st == "COMPLETED":
            completed_count += 1
        elif st == "BLOCKED":
            blocked_count += 1
        elif st == "IN_PROGRESS":
            in_progress_count += 1

        if is_overdue:
            overdue_count += 1

        if not t.owner or not t.owner.strip():
            unassigned_count += 1

        # Associate related dependencies
        task_topic = clean_core_topic(t.title)
        related_deps = []
        for dep in deps:
            dep_topic = clean_core_topic(dep.title)
            dep_rel = clean_core_topic(dep.related_entity or "")
            if task_topic in dep_topic or task_topic in dep_rel or dep_rel in task_topic:
                related_deps.append(dep.title)

        timeline_items.append(TaskTimelineItem(
            id=t.id,
            title=t.title,
            description=t.description,
            owner=t.owner,
            has_owner=bool(t.owner and t.owner.strip()),
            deadline=t.deadline,
            normalized_deadline=iso_deadline,
            has_deadline=bool(iso_deadline),
            start_date=None,  # Do not invent start date
            task_status=st,
            priority=t.priority or "MEDIUM",
            is_overdue=is_overdue,
            dependencies=related_deps,
            supporting_quotation=t.supporting_quotation,
            page_number=t.page_number or 1,
            document_filename=doc.filename if doc else None,
            verification_status=t.verification_status
        ))

    # Sort items: dated tasks sorted by deadline ascending; undated tasks appended
    timeline_items.sort(key=lambda item: (0 if item.has_deadline else 1, item.normalized_deadline or ""))

    return TaskTimelineResponse(
        tasks=timeline_items,
        total_tasks=len(timeline_items),
        completed_count=completed_count,
        in_progress_count=in_progress_count,
        blocked_count=blocked_count,
        overdue_count=overdue_count,
        unassigned_count=unassigned_count
    )

def get_dependency_graph(
    project_id: str,
    db: Session
) -> DependencyGraphResponse:
    """
    Constructs a directional relationship graph between project entities.
    Detects circular dependencies and identifies unfulfilled prerequisites.
    """
    findings = db.query(ExtractedFinding).filter(ExtractedFinding.project_id == project_id).all()
    deps = [f for f in findings if f.entity_type == "DEPENDENCY"]
    tasks = [f for f in findings if f.entity_type == "TASK"]
    decisions = [f for f in findings if f.entity_type == "DECISION"]

    nodes: List[DependencyGraphNode] = []
    edges: List[DependencyGraphEdge] = []
    node_id_map: Dict[str, DependencyGraphNode] = {}
    label_to_id: Dict[str, str] = {}

    def get_or_create_node(entity_id: str, label: str, entity_type: str, f: Optional[ExtractedFinding] = None) -> str:
        clean_lbl = label.strip()
        core_lbl = clean_core_topic(clean_lbl)
        if core_lbl in label_to_id:
            return label_to_id[core_lbl]

        doc = db.query(Document).filter(Document.id == f.document_id).first() if (f and f.document_id) else None
        node = DependencyGraphNode(
            id=entity_id,
            label=clean_lbl,
            entity_type=entity_type,
            status=f.task_status if f else None,
            owner=f.owner if f else None,
            supporting_quotation=f.supporting_quotation if f else None,
            page_number=f.page_number if f else 1,
            document_filename=doc.filename if doc else None
        )
        nodes.append(node)
        node_id_map[entity_id] = node
        label_to_id[core_lbl] = entity_id
        return entity_id

    # 1. Register Tasks and Decisions as base nodes
    for t in tasks:
        get_or_create_node(t.id, t.title, "TASK", t)
    for d in decisions:
        get_or_create_node(d.id, d.title, "DECISION", d)

    # 2. Build edges from DEPENDENCY findings
    # Format e.g., "Database migration depends on PostgreSQL upgrade"
    # or "Payment integration depends on Database migration"
    missing_prereqs = []
    adjacency: Dict[str, List[str]] = {}

    for idx, dep in enumerate(deps):
        doc = db.query(Document).filter(Document.id == dep.document_id).first() if dep.document_id else None
        quote = dep.supporting_quotation or dep.description

        # Extract target dependency entity
        target_name = dep.related_entity or ""
        source_name = dep.title

        # Check if source or target can be linked to existing task
        matched_target_ids = resolve_entity_links(target_name, [{"id": n.id, "title": n.label, "description": ""} for n in nodes])
        matched_source_ids = resolve_entity_links(source_name, [{"id": n.id, "title": n.label, "description": ""} for n in nodes])

        target_node_id = matched_target_ids[0] if matched_target_ids else None
        source_node_id = matched_source_ids[0] if matched_source_ids else None

        if not target_node_id and target_name:
            # Create synthetic unfulfilled prerequisite node
            target_node_id = f"prereq-{idx}"
            get_or_create_node(target_node_id, target_name.title(), "PREREQUISITE", dep)
            missing_prereqs.append(target_name.strip())

        if not source_node_id:
            source_node_id = get_or_create_node(dep.id, dep.title, "TASK", dep)

        if source_node_id and target_node_id and source_node_id != target_node_id:
            # Directional edge: Prerequisite (target) -> Dependent Task (source)
            edge = DependencyGraphEdge(
                id=f"edge-{source_node_id}-{target_node_id}",
                source=target_node_id,
                target=source_node_id,
                relationship_type="DEPENDS_ON",
                source_evidence=quote,
                page_number=dep.page_number or 1,
                document_filename=doc.filename if doc else None
            )
            edges.append(edge)
            adjacency.setdefault(target_node_id, []).append(source_node_id)

    # 3. Circular Dependency Detection (DFS)
    visited: Set[str] = set()
    rec_stack: Set[str] = set()
    cycles: List[List[str]] = []

    def dfs(curr: str, path: List[str]):
        visited.add(curr)
        rec_stack.add(curr)
        path.append(curr)

        for neighbor in adjacency.get(curr, []):
            if neighbor not in visited:
                dfs(neighbor, path)
            elif neighbor in rec_stack:
                cycle_slice = path[path.index(neighbor):] + [neighbor]
                cycles.append(cycle_slice)

        rec_stack.remove(curr)
        path.pop()

    for node in nodes:
        if node.id not in visited:
            dfs(node.id, [])

    return DependencyGraphResponse(
        nodes=nodes,
        edges=edges,
        has_cycle=len(cycles) > 0,
        cycles=cycles,
        missing_prerequisites=missing_prereqs
    )

def get_responsibilities(
    project_id: str,
    db: Session
) -> ResponsibilitiesResponse:
    """
    Constructs responsibility mapping across team members.
    Explicitly flags unassigned tasks. Never assigns to PM automatically.
    """
    tasks = db.query(ExtractedFinding).filter(
        ExtractedFinding.project_id == project_id,
        ExtractedFinding.entity_type == "TASK"
    ).all()

    members = db.query(ProjectMember).filter(ProjectMember.project_id == project_id).all()
    member_by_name: Dict[str, ProjectMember] = {}
    for m in members:
        u = db.query(User).filter(User.id == m.user_id).first()
        if u and u.full_name:
            member_by_name[u.full_name.lower().strip()] = m

    owner_groups: Dict[str, List[ExtractedFinding]] = {}
    unassigned_tasks: List[Dict[str, Any]] = []

    for t in tasks:
        owner = t.owner.strip() if t.owner else None
        if not owner:
            unassigned_tasks.append({
                "id": t.id,
                "title": t.title,
                "description": t.description,
                "task_status": t.task_status or "UNKNOWN",
                "deadline": t.deadline,
                "supporting_quotation": t.supporting_quotation,
                "page_number": t.page_number
            })
        else:
            owner_groups.setdefault(owner, []).append(t)

    owners_list: List[OwnerResponsibilityItem] = []
    for owner_name, task_list in owner_groups.items():
        pm = member_by_name.get(owner_name.lower())
        completed = sum(1 for item in task_list if normalize_task_status(item.task_status, item.description) == "COMPLETED")
        blocked = sum(1 for item in task_list if normalize_task_status(item.task_status, item.description) == "BLOCKED")
        in_prog = sum(1 for item in task_list if normalize_task_status(item.task_status, item.description) == "IN_PROGRESS")
        pending = sum(1 for item in task_list if normalize_task_status(item.task_status, item.description) == "NOT_STARTED")

        owners_list.append(OwnerResponsibilityItem(
            owner_name=owner_name,
            is_registered_member=bool(pm),
            role=pm.role if pm else None,
            total_assigned=len(task_list),
            completed_count=completed,
            in_progress_count=in_prog,
            blocked_count=blocked,
            pending_count=pending,
            tasks=[{
                "id": item.id,
                "title": item.title,
                "description": item.description,
                "task_status": item.task_status or "UNKNOWN",
                "deadline": item.deadline,
                "page_number": item.page_number
            } for item in task_list]
        ))

    # Sort owners by workload descending
    owners_list.sort(key=lambda o: o.total_assigned, reverse=True)

    return ResponsibilitiesResponse(
        owners=owners_list,
        unassigned_tasks=unassigned_tasks,
        unassigned_count=len(unassigned_tasks),
        total_tasks=len(tasks)
    )

def get_risk_register(
    project_id: str,
    db: Session
) -> RiskRegisterResponse:
    """
    Consolidates risks and blockers, distinguishing source-extracted risks
    from AI-generated recommendations. Never invents severity/likelihood.
    """
    findings = db.query(ExtractedFinding).filter(
        ExtractedFinding.project_id == project_id,
        ExtractedFinding.entity_type.in_(["RISK", "BLOCKER"])
    ).all()

    source_risks: List[RiskRegisterItem] = []
    blockers: List[RiskRegisterItem] = []
    ai_recommendations: List[RiskRegisterItem] = []
    critical_count = 0

    for f in findings:
        doc = db.query(Document).filter(Document.id == f.document_id).first() if f.document_id else None
        
        # Severity / impact determination without hallucination
        raw_sev = (f.priority or f.impact or "").upper()
        if any(w in raw_sev for w in ["CRITICAL", "SEVERE", "FATAL"]):
            severity = "CRITICAL"
        elif any(w in raw_sev for w in ["HIGH", "ELEVATED"]):
            severity = "HIGH"
        elif any(w in raw_sev for w in ["MEDIUM", "MODERATE"]):
            severity = "MEDIUM"
        elif any(w in raw_sev for w in ["LOW", "MINOR"]):
            severity = "LOW"
        else:
            severity = "UNKNOWN"

        if severity == "CRITICAL":
            critical_count += 1

        raw_like = (f.likelihood or "").upper()
        if "HIGH" in raw_like:
            likelihood = "HIGH"
        elif "LOW" in raw_like:
            likelihood = "LOW"
        elif "MED" in raw_like:
            likelihood = "MEDIUM"
        else:
            likelihood = "UNKNOWN"

        category = "AI_RECOMMENDATION" if f.is_recommendation else "SOURCE_IDENTIFIED"

        item = RiskRegisterItem(
            id=f.id,
            title=f.title,
            description=f.description,
            category=category,
            severity=severity,
            likelihood=likelihood,
            mitigation=f.mitigation,
            related_tasks=[],
            supporting_quotation=f.supporting_quotation,
            page_number=f.page_number or 1,
            document_filename=doc.filename if doc else None,
            verification_status=f.verification_status
        )

        if f.is_recommendation:
            ai_recommendations.append(item)
        elif f.entity_type == "BLOCKER":
            blockers.append(item)
        else:
            source_risks.append(item)

    return RiskRegisterResponse(
        source_risks=source_risks,
        blockers=blockers,
        ai_recommendations=ai_recommendations,
        total_risks=len(findings),
        critical_count=critical_count
    )

def search_project_knowledge(
    project_id: str,
    query_str: str,
    db: Session,
    entity_type_filter: Optional[str] = None
) -> KnowledgeSearchResponse:
    """
    Project-scoped search across all extracted project findings.
    Enforces authorization and returns matched findings with source citations.
    """
    if not query_str or not query_str.strip():
        return KnowledgeSearchResponse(query="", total_results=0, results=[])

    clean_q = query_str.strip().lower()
    search_fmt = f"%{clean_q}%"

    query = db.query(ExtractedFinding).filter(
        ExtractedFinding.project_id == project_id,
        or_(
            ExtractedFinding.title.ilike(search_fmt),
            ExtractedFinding.description.ilike(search_fmt),
            ExtractedFinding.owner.ilike(search_fmt),
            ExtractedFinding.supporting_quotation.ilike(search_fmt),
            ExtractedFinding.related_entity.ilike(search_fmt)
        )
    )

    if entity_type_filter and entity_type_filter.upper() != "ALL":
        query = query.filter(ExtractedFinding.entity_type == entity_type_filter.upper())

    matched_findings = query.order_by(ExtractedFinding.created_at.desc()).all()

    results: List[KnowledgeSearchItem] = []
    for f in matched_findings:
        doc = db.query(Document).filter(Document.id == f.document_id).first() if f.document_id else None
        
        # Build matching snippet
        snippet = f.supporting_quotation or f.description
        results.append(KnowledgeSearchItem(
            id=f.id,
            title=f.title,
            description=f.description,
            entity_type=f.entity_type,
            owner=f.owner,
            status=f.task_status or f.status,
            source_document=doc.filename if doc else None,
            page_number=f.page_number or 1,
            supporting_quotation=f.supporting_quotation,
            verification_status=f.verification_status,
            confidence_score=f.confidence_score or 1.0,
            match_snippet=snippet[:250] if snippet else None
        ))

    return KnowledgeSearchResponse(
        query=query_str,
        total_results=len(results),
        results=results
    )
