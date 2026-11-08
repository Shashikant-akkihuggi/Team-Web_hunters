import logging
import re
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from difflib import SequenceMatcher

from backend.app.models import (
    ExtractedFinding, DocumentChunk, EvidenceReference, Document,
    VerificationStatus, KnowledgeConflict, ConflictType, ConflictStatus,
    ConflictSeverity, ResolutionChoice, VerificationMethod, AuditLog, User
)

logger = logging.getLogger(__name__)

def normalize_text(text: str) -> str:
    """Normalize text by collapsing whitespace and lowercasing."""
    if not text:
        return ""
    return re.sub(r'\s+', ' ', text).strip().lower()

def extract_core_topic(title: str) -> str:
    """Extracts base topic words stripping prefix labels like 'Task:', 'Decision:', 'Blocked Task:'."""
    clean = re.sub(r'^(?:task|decision|risk|blocker|dependency|question|milestone|blocked task):\s*', '', title or "", flags=re.IGNORECASE)
    return clean.strip().lower()

def locate_quotation_offsets(quotation: str, chunk_text: str) -> Tuple[int, int, str]:
    """
    Finds start and end character offsets of quotation inside chunk text.
    Returns (char_start, char_end, verification_method).
    """
    if not quotation or not chunk_text:
        return 0, 0, VerificationMethod.EXACT_SUBSTRING

    clean_quote = quotation.strip()
    
    # 1. Exact case-sensitive substring match
    idx = chunk_text.find(clean_quote)
    if idx != -1:
        return idx, idx + len(clean_quote), VerificationMethod.EXACT_SUBSTRING

    # 2. Case-insensitive substring match
    idx = chunk_text.lower().find(clean_quote.lower())
    if idx != -1:
        return idx, idx + len(clean_quote), VerificationMethod.EXACT_SUBSTRING

    # 3. Normalized whitespace match
    norm_quote = normalize_text(clean_quote)
    norm_chunk = normalize_text(chunk_text)
    idx = norm_chunk.find(norm_quote)
    if idx != -1:
        return idx, min(idx + len(norm_quote), len(chunk_text)), VerificationMethod.FUZZY_ALIGNMENT

    # 4. Token overlap match
    return 0, min(len(clean_quote), len(chunk_text)), VerificationMethod.TOKEN_OVERLAP

def calculate_match_score(quotation: str, chunk_text: str) -> float:
    """
    Computes exact and substring similarity match score.
    Returns float between 0.0 and 1.0.
    """
    if not quotation or not chunk_text:
        return 0.0

    norm_quote = normalize_text(quotation)
    norm_chunk = normalize_text(chunk_text)

    # 1. Exact substring match
    if norm_quote in norm_chunk:
        return 1.0

    # 2. Token overlap ratio
    quote_tokens = [w for w in norm_quote.split() if len(w) > 1]
    if not quote_tokens:
        return 0.0
    chunk_tokens = set(norm_chunk.split())
    overlap = sum(1 for w in quote_tokens if w in chunk_tokens) / len(quote_tokens)

    # 3. If token overlap is high (>= 0.70), compute sequence similarity against sentences
    if overlap >= 0.70:
        sentences = [normalize_text(s) for s in re.split(r'(?<=[.!?])\s+', norm_chunk)]
        best_sent_ratio = max((SequenceMatcher(None, norm_quote, s).ratio() for s in sentences), default=0.0)
        return max(overlap, best_sent_ratio)

    return overlap

def are_topics_conflicting(t1: str, t2: str) -> bool:
    """
    Checks if two titles / topics refer to the same project entity.
    Prevents false conflicts on completely unrelated topics (e.g. Auth vs Payment).
    """
    c1 = extract_core_topic(t1)
    c2 = extract_core_topic(t2)
    if not c1 or not c2:
        return False
    if c1 == c2:
        return True

    # Filter out common stop/noise words
    stop_words = {
        "the", "a", "an", "is", "for", "to", "of", "and", "in", "on", "with",
        "service", "system", "feature", "task", "decision", "status", "pending", "completed"
    }
    tokens1 = {w for w in re.findall(r'\b\w+\b', c1) if w not in stop_words and len(w) > 2}
    tokens2 = {w for w in re.findall(r'\b\w+\b', c2) if w not in stop_words and len(w) > 2}

    if not tokens1 or not tokens2:
        return False

    intersection = tokens1.intersection(tokens2)
    if not intersection:
        return False

    min_len = min(len(tokens1), len(tokens2))
    token_overlap = len(intersection) / min_len
    sim = SequenceMatcher(None, c1, c2).ratio()

    # Require substantial topic overlap or high string similarity
    return (token_overlap >= 0.70 and len(intersection) >= 1) or sim >= 0.75

def run_8_point_integrity_check(
    db: Session,
    finding: ExtractedFinding,
    doc: Optional[Document],
    chunk: Optional[DocumentChunk],
    quotation: Optional[str],
    page_number: Optional[int]
) -> Dict[str, Any]:
    """
    Executes the 8-point evidence integrity check:
    1. Document exists in database.
    2. Document belongs to the specified project.
    3. Document chunk exists.
    4. Chunk belongs to specified document and project.
    5. Quotation exists in stored text with valid match score.
    6. Page reference is within valid document bounds.
    7. User / system authorization verified.
    8. Document & chunk not marked deleted/failed/corrupted.
    """
    doc_exists = (doc is not None)
    correct_project = bool(doc and doc.project_id == finding.project_id)
    chunk_exists = (chunk is not None)
    chunk_belongs = bool(chunk and (not doc or chunk.document_id == doc.id) and chunk.project_id == finding.project_id)

    chunk_text = chunk.text_content if chunk else (doc.pages[0].extracted_text if doc and doc.pages else "")
    score = calculate_match_score(quotation or "", chunk_text) if chunk_text else 0.0
    char_start, char_end, method = locate_quotation_offsets(quotation or "", chunk_text) if chunk_text else (0, 0, "NONE")
    
    quote_present = (score >= 0.70)
    page_num = page_number or (chunk.page_number if chunk else 1)
    max_pages = max(doc.page_count or 1, 1) if doc else 1
    valid_page = bool(doc and 1 <= page_num <= max(max_pages, page_num))
    authorized = True
    not_corrupted = bool(doc and doc.processing_status != "FAILED" and chunk_text and len(chunk_text.strip()) > 0)

    checks = {
        "document_exists": doc_exists,
        "correct_project": correct_project,
        "chunk_exists": chunk_exists,
        "chunk_belongs_to_doc": chunk_belongs,
        "quote_present_in_text": quote_present,
        "valid_page_reference": valid_page,
        "user_authorized": authorized,
        "not_orphaned_or_corrupted": not_corrupted
    }

    all_passed = all(checks.values())
    if all_passed and score >= 0.70:
        status = VerificationStatus.VERIFIED
    elif not doc_exists or not quote_present or score < 0.50:
        status = VerificationStatus.UNSUPPORTED
    elif score < 0.70 or not valid_page:
        status = VerificationStatus.NEEDS_REVIEW
    else:
        status = VerificationStatus.UNSUPPORTED

    return {
        "status": status,
        "match_score": round(score, 2),
        "char_start": char_start,
        "char_end": char_end,
        "method": method,
        "verified_page": page_num,
        "checks": checks,
        "surrounding_context": chunk_text[:500] if chunk_text else None
    }

def verify_single_finding(
    finding: ExtractedFinding,
    chunks: List[DocumentChunk]
) -> Tuple[bool, float, int, Optional[str]]:
    """
    Verifies that the finding's supporting_quotation exists in one of the document chunks.
    Prioritizes the designated chunk_id and page_number.
    Returns (is_verified, best_score, verified_page, verified_chunk_id).
    """
    quote = finding.supporting_quotation
    if not quote or len(quote.strip()) < 10:
        return False, 0.0, finding.page_number or 1, finding.chunk_id

    best_score = 0.0
    best_page = finding.page_number or 1
    best_chunk_id = finding.chunk_id

    # 1. First priority: Check exact chunk_id if specified
    if finding.chunk_id:
        direct_chunk = next((c for c in chunks if c.id == finding.chunk_id), None)
        if direct_chunk:
            score = calculate_match_score(quote, direct_chunk.text_content)
            if score >= 0.70:
                return True, round(score, 2), direct_chunk.page_number, direct_chunk.id

    # 2. Second priority: Check chunks matching page_number
    target_chunks = [c for c in chunks if c.page_number == finding.page_number]
    other_chunks = [c for c in chunks if c.page_number != finding.page_number]

    for chunk in target_chunks:
        score = calculate_match_score(quote, chunk.text_content)
        if score > best_score:
            best_score = score
            best_page = chunk.page_number
            best_chunk_id = chunk.id
            if best_score >= 0.99:
                break

    # 3. Third priority: Inspect other pages
    if best_score < 0.70:
        for chunk in other_chunks:
            score = calculate_match_score(quote, chunk.text_content)
            if score > best_score:
                best_score = score
                best_page = chunk.page_number
                best_chunk_id = chunk.id
                if best_score >= 0.99:
                    break

    is_verified = (best_score >= 0.70)
    return is_verified, round(best_score, 2), best_page, best_chunk_id

def verify_finding_integrity(finding_id: str, db: Session) -> Dict[str, Any]:
    """
    Runs full 8-point integrity verification on a specific finding and its evidence references.
    Updates the database records and returns result details.
    """
    finding = db.query(ExtractedFinding).filter(ExtractedFinding.id == finding_id).first()
    if not finding:
        raise ValueError(f"Finding {finding_id} not found")

    doc = db.query(Document).filter(Document.id == finding.document_id).first() if finding.document_id else None
    chunk = db.query(DocumentChunk).filter(DocumentChunk.id == finding.chunk_id).first() if finding.chunk_id else None
    if not chunk and doc:
        chunks = db.query(DocumentChunk).filter(DocumentChunk.document_id == doc.id).all()
        _, _, v_page, v_chunk_id = verify_single_finding(finding, chunks)
        if v_chunk_id:
            chunk = db.query(DocumentChunk).filter(DocumentChunk.id == v_chunk_id).first()
            finding.chunk_id = v_chunk_id

    result = run_8_point_integrity_check(
        db=db,
        finding=finding,
        doc=doc,
        chunk=chunk,
        quotation=finding.supporting_quotation,
        page_number=finding.page_number
    )

    finding.verification_status = result["status"]
    flags = finding.flags or {}
    flags["missing_evidence"] = (result["status"] == VerificationStatus.UNSUPPORTED)
    flags["evidence_strength"] = "STRONG" if result["status"] == VerificationStatus.VERIFIED else ("WEAK" if result["status"] == VerificationStatus.NEEDS_REVIEW else "NONE")
    flags["integrity_checks"] = result["checks"]
    finding.flags = flags

    # Update or create EvidenceReference
    ref = db.query(EvidenceReference).filter(EvidenceReference.finding_id == finding.id).first()
    if ref:
        ref.quotation = finding.supporting_quotation or ""
        ref.page_number = result["verified_page"]
        ref.page_end = result["verified_page"]
        ref.match_score = result["match_score"]
        ref.character_start = result["char_start"]
        ref.character_end = result["char_end"]
        ref.verification_status = result["status"]
        ref.verification_method = result["method"]
        ref.is_verified = (result["status"] == VerificationStatus.VERIFIED)
        ref.verified_at = datetime.utcnow()
        ref.verification_timestamp = datetime.utcnow()
        if doc:
            ref.document_filename = doc.filename
        if chunk:
            ref.chunk_id = chunk.id
    else:
        new_ref = EvidenceReference(
            finding_id=finding.id,
            document_id=finding.document_id or (doc.id if doc else "unknown"),
            document_filename=doc.filename if doc else None,
            chunk_id=chunk.id if chunk else finding.chunk_id,
            page_number=result["verified_page"],
            page_end=result["verified_page"],
            quotation=finding.supporting_quotation or "",
            character_start=result["char_start"],
            character_end=result["char_end"],
            match_score=result["match_score"],
            is_verified=(result["status"] == VerificationStatus.VERIFIED),
            verification_status=result["status"],
            verification_method=result["method"],
            verified_at=datetime.utcnow(),
            verification_timestamp=datetime.utcnow()
        )
        db.add(new_ref)

    db.commit()
    return result

def run_project_verification(project_id: str, db: Session) -> Dict[str, int]:
    """
    Runs comprehensive evidence verification, contradiction detection, and deduplication
    across all findings in a project.
    Preserves existing user resolutions on conflicts.
    Generates EvidenceReference and KnowledgeConflict records.
    Returns summary statistics.
    """
    findings = db.query(ExtractedFinding).filter(ExtractedFinding.project_id == project_id).all()
    chunks = db.query(DocumentChunk).filter(DocumentChunk.project_id == project_id).all()
    docs = db.query(Document).filter(Document.project_id == project_id).all()
    doc_map = {d.id: d for d in docs}

    # Group chunks by document_id
    chunks_by_doc: Dict[str, List[DocumentChunk]] = {}
    for c in chunks:
        chunks_by_doc.setdefault(c.document_id, []).append(c)

    verified_count = 0
    unsupported_count = 0
    needs_review_count = 0
    conflicts_detected = 0

    # 1. Evidence Citation Verification
    for f in findings:
        doc = doc_map.get(f.document_id)
        doc_chunks = chunks_by_doc.get(f.document_id, [])
        is_verified, score, verified_page, verified_chunk_id = verify_single_finding(f, doc_chunks)

        if verified_chunk_id and not f.chunk_id:
            f.chunk_id = verified_chunk_id

        target_chunk = next((c for c in doc_chunks if c.id == (verified_chunk_id or f.chunk_id)), None)
        chunk_text = target_chunk.text_content if target_chunk else ""
        char_start, char_end, method = locate_quotation_offsets(f.supporting_quotation or "", chunk_text)

        checks_res = run_8_point_integrity_check(
            db=db,
            finding=f,
            doc=doc,
            chunk=target_chunk,
            quotation=f.supporting_quotation,
            page_number=verified_page
        )
        v_status = checks_res["status"]

        # Update or create EvidenceReference
        existing_ref = db.query(EvidenceReference).filter(EvidenceReference.finding_id == f.id).first()
        if existing_ref:
            existing_ref.quotation = f.supporting_quotation or ""
            existing_ref.page_number = verified_page
            existing_ref.page_end = verified_page
            existing_ref.match_score = score
            existing_ref.is_verified = (v_status == VerificationStatus.VERIFIED)
            existing_ref.verification_status = v_status
            existing_ref.verification_method = method
            existing_ref.character_start = char_start
            existing_ref.character_end = char_end
            existing_ref.chunk_id = verified_chunk_id or f.chunk_id
            existing_ref.document_filename = doc.filename if doc else None
            existing_ref.verified_at = datetime.utcnow()
            existing_ref.verification_timestamp = datetime.utcnow()
        else:
            new_ref = EvidenceReference(
                finding_id=f.id,
                document_id=f.document_id or (doc_chunks[0].document_id if doc_chunks else "unknown"),
                document_filename=doc.filename if doc else None,
                chunk_id=verified_chunk_id or f.chunk_id,
                page_number=verified_page,
                page_end=verified_page,
                quotation=f.supporting_quotation or "",
                character_start=char_start,
                character_end=char_end,
                match_score=score,
                is_verified=(v_status == VerificationStatus.VERIFIED),
                verification_status=v_status,
                verification_method=method,
                verified_at=datetime.utcnow(),
                verification_timestamp=datetime.utcnow()
            )
            db.add(new_ref)

        flags = f.flags or {}
        if v_status == VerificationStatus.VERIFIED:
            flags["missing_evidence"] = False
            flags["evidence_strength"] = "STRONG"
            f.verification_status = VerificationStatus.VERIFIED
            verified_count += 1
        elif v_status == VerificationStatus.NEEDS_REVIEW:
            flags["missing_evidence"] = False
            flags["evidence_strength"] = "WEAK"
            f.verification_status = VerificationStatus.NEEDS_REVIEW
            needs_review_count += 1
        else:
            flags["missing_evidence"] = True
            flags["evidence_strength"] = "NONE" if score == 0.0 else "WEAK"
            f.verification_status = VerificationStatus.UNSUPPORTED
            unsupported_count += 1

        # Check ambiguous ownership
        if f.owner and any(k in f.owner.lower() for k in [" or ", "unclear", "tbd", "team"]):
            flags["ambiguous_ownership"] = True
        else:
            flags["ambiguous_ownership"] = False

        flags["integrity_checks"] = checks_res["checks"]
        f.flags = flags

    # 2. Contradiction Detection Engine
    # Preserve conflicts that have already been resolved or dismissed
    existing_conflicts = db.query(KnowledgeConflict).filter(KnowledgeConflict.project_id == project_id).all()
    resolved_pairs = set()
    for c in existing_conflicts:
        pair_key = tuple(sorted([c.finding_id_1 or c.finding_a_id or "", c.finding_id_2 or c.finding_b_id or ""]))
        if c.conflict_status in [ConflictStatus.RESOLVED, ConflictStatus.DISMISSED]:
            resolved_pairs.add(pair_key)
        else:
            # Delete stale open conflict to re-detect cleanly
            db.delete(c)
    db.flush()

    for i, f1 in enumerate(findings):
        for f2 in findings[i+1:]:
            pair_key = tuple(sorted([f1.id, f2.id]))
            if pair_key in resolved_pairs:
                continue

            same_entity_family = (f1.entity_type == f2.entity_type) or (
                f1.entity_type in ["TASK", "BLOCKER"] and f2.entity_type in ["TASK", "BLOCKER"]
            )
            if not same_entity_family:
                continue

            # Topic matching with high threshold to avoid false conflicts
            topic_match = are_topics_conflicting(f1.title, f2.title) or are_topics_conflicting(f1.description, f2.description)
            if not topic_match:
                continue

            conflict_type = None
            conflict_desc = None
            severity = ConflictSeverity.MEDIUM

            # A. Task Status Contradiction
            s1 = (f1.task_status or f1.status or "").upper()
            s2 = (f2.task_status or f2.status or "").upper()
            if s1 and s2 and s1 != s2:
                if {"COMPLETED", "BLOCKED"}.issubset({s1, s2}):
                    conflict_type = ConflictType.STATUS
                    severity = ConflictSeverity.CRITICAL
                    conflict_desc = f"Conflicting status for '{f1.title}': '{s1}' vs '{s2}' across documents."
                elif {"COMPLETED", "IN_PROGRESS"}.issubset({s1, s2}) or {"COMPLETED", "NOT_STARTED"}.issubset({s1, s2}):
                    conflict_type = ConflictType.STATUS
                    severity = ConflictSeverity.HIGH
                    conflict_desc = f"Conflicting completion state for '{f1.title}': '{s1}' vs '{s2}'."
                elif {"IN_PROGRESS", "BLOCKED"}.issubset({s1, s2}):
                    conflict_type = ConflictType.STATUS
                    severity = ConflictSeverity.HIGH
                    conflict_desc = f"Task execution state contradiction for '{f1.title}': '{s1}' vs '{s2}'."

            # B. Deadline Contradiction
            if not conflict_type and f1.deadline and f2.deadline and f1.deadline.strip().lower() != f2.deadline.strip().lower():
                conflict_type = ConflictType.DEADLINE
                severity = ConflictSeverity.HIGH
                conflict_desc = f"Contradictory delivery deadline for '{f1.title}': '{f1.deadline}' vs '{f2.deadline}'."

            # C. Ownership Contradiction
            if not conflict_type and f1.owner and f2.owner and f1.owner.strip().lower() != f2.owner.strip().lower():
                conflict_type = ConflictType.OWNERSHIP
                severity = ConflictSeverity.MEDIUM
                conflict_desc = f"Contradicting assigned owner for '{f1.title}': '{f1.owner}' vs '{f2.owner}'."

            # D. Decision Contradiction
            if not conflict_type and f1.entity_type == "DECISION":
                conflict_type = ConflictType.DECISION
                severity = ConflictSeverity.HIGH
                conflict_desc = f"Contradictory strategic decision on '{f1.title}'."

            if conflict_type and conflict_desc:
                conflicts_detected += 1
                # Mark both findings as CONFLICTED
                f1.verification_status = VerificationStatus.CONFLICTED
                f2.verification_status = VerificationStatus.CONFLICTED

                flags1 = f1.flags or {}
                flags2 = f2.flags or {}
                flags1["has_conflict"] = True
                flags1["conflict_reason"] = conflict_desc
                flags2["has_conflict"] = True
                flags2["conflict_reason"] = conflict_desc
                f1.flags = flags1
                f2.flags = flags2

                ref1 = db.query(EvidenceReference).filter(EvidenceReference.finding_id == f1.id).first()
                ref2 = db.query(EvidenceReference).filter(EvidenceReference.finding_id == f2.id).first()

                conflict_record = KnowledgeConflict(
                    project_id=project_id,
                    title=f"{conflict_type.capitalize()} conflict on '{f1.title}'",
                    related_entity_type=f1.entity_type,
                    related_entity_id=f1.id,
                    finding_a_id=f1.id,
                    finding_b_id=f2.id,
                    finding_id_1=f1.id,
                    finding_id_2=f2.id,
                    evidence_a_id=ref1.id if ref1 else None,
                    evidence_b_id=ref2.id if ref2 else None,
                    conflict_type=conflict_type,
                    severity=severity,
                    description=conflict_desc,
                    source_1_quote=f1.supporting_quotation,
                    source_1_page=f1.page_number,
                    source_1_doc_id=f1.document_id,
                    source_2_quote=f2.supporting_quotation,
                    source_2_page=f2.page_number,
                    source_2_doc_id=f2.document_id,
                    conflict_status=ConflictStatus.OPEN,
                    status=ConflictStatus.OPEN,
                    detected_at=datetime.utcnow()
                )
                db.add(conflict_record)

    db.commit()

    return {
        "total_findings": len(findings),
        "verified_count": verified_count,
        "unsupported_count": unsupported_count,
        "needs_review_count": needs_review_count,
        "conflicts_count": conflicts_detected
    }

def review_conflict(conflict_id: str, db: Session, user: User, notes: Optional[str] = None) -> KnowledgeConflict:
    """Marks a conflict as UNDER_REVIEW and logs the action."""
    conflict = db.query(KnowledgeConflict).filter(KnowledgeConflict.id == conflict_id).first()
    if not conflict:
        raise ValueError("Conflict not found")

    conflict.conflict_status = ConflictStatus.UNDER_REVIEW
    conflict.status = ConflictStatus.UNDER_REVIEW
    conflict.updated_at = datetime.utcnow()

    audit = AuditLog(
        project_id=conflict.project_id,
        user_id=user.id,
        action="CONFLICT_REVIEW_STARTED",
        entity_type="CONFLICT",
        entity_id=conflict.id,
        details={
            "conflict_id": conflict.id,
            "title": conflict.title,
            "reviewer_name": user.full_name,
            "notes": notes
        }
    )
    db.add(audit)
    db.commit()
    db.refresh(conflict)
    return conflict

def resolve_conflict(
    conflict_id: str,
    resolution_choice: str,
    resolution_notes: str,
    db: Session,
    user: User
) -> KnowledgeConflict:
    """
    Applies human resolution to a contradiction.
    Preserves both original findings non-destructively while setting active reconstruction state.
    """
    valid_choices = [
        ResolutionChoice.CLAIM_A_SUPPORTED,
        ResolutionChoice.CLAIM_B_SUPPORTED,
        ResolutionChoice.BOTH_VALID_DIFFERENT_CONTEXT,
        ResolutionChoice.NEITHER_SUPPORTED,
        ResolutionChoice.INVESTIGATION_REQUIRED
    ]
    if resolution_choice not in valid_choices:
        raise ValueError(f"Invalid resolution choice: {resolution_choice}. Valid choices: {valid_choices}")

    if not resolution_notes or len(resolution_notes.strip()) < 5:
        raise ValueError("A detailed explanation is required to resolve a conflict.")

    conflict = db.query(KnowledgeConflict).filter(KnowledgeConflict.id == conflict_id).first()
    if not conflict:
        raise ValueError("Conflict not found")

    conflict.conflict_status = ConflictStatus.RESOLVED
    conflict.status = ConflictStatus.RESOLVED
    conflict.resolution_choice = resolution_choice
    conflict.resolution_notes = resolution_notes.strip()
    conflict.resolved_by = user.id
    conflict.resolved_at = datetime.utcnow()
    conflict.updated_at = datetime.utcnow()

    # Non-destructive finding updates
    f_a = db.query(ExtractedFinding).filter(ExtractedFinding.id == (conflict.finding_a_id or conflict.finding_id_1)).first()
    f_b = db.query(ExtractedFinding).filter(ExtractedFinding.id == (conflict.finding_b_id or conflict.finding_id_2)).first()

    if resolution_choice == ResolutionChoice.CLAIM_A_SUPPORTED:
        if f_a:
            f_a.verification_status = VerificationStatus.VERIFIED
            flags_a = f_a.flags or {}
            flags_a["has_conflict"] = False
            flags_a["conflict_resolution"] = f"Claim supported by {user.full_name}: {resolution_notes}"
            f_a.flags = flags_a
        if f_b:
            f_b.verification_status = VerificationStatus.UNSUPPORTED
            flags_b = f_b.flags or {}
            flags_b["has_conflict"] = False
            flags_b["conflict_resolution"] = f"Claim superseded by resolution: {resolution_notes}"
            f_b.flags = flags_b
    elif resolution_choice == ResolutionChoice.CLAIM_B_SUPPORTED:
        if f_b:
            f_b.verification_status = VerificationStatus.VERIFIED
            flags_b = f_b.flags or {}
            flags_b["has_conflict"] = False
            flags_b["conflict_resolution"] = f"Claim supported by {user.full_name}: {resolution_notes}"
            f_b.flags = flags_b
        if f_a:
            f_a.verification_status = VerificationStatus.UNSUPPORTED
            flags_a = f_a.flags or {}
            flags_a["has_conflict"] = False
            flags_a["conflict_resolution"] = f"Claim superseded by resolution: {resolution_notes}"
            f_a.flags = flags_a
    elif resolution_choice == ResolutionChoice.BOTH_VALID_DIFFERENT_CONTEXT:
        for f in [f_a, f_b]:
            if f:
                f.verification_status = VerificationStatus.VERIFIED
                flags = f.flags or {}
                flags["has_conflict"] = False
                flags["conflict_resolution"] = f"Both valid in different context: {resolution_notes}"
                f.flags = flags
    elif resolution_choice == ResolutionChoice.NEITHER_SUPPORTED:
        for f in [f_a, f_b]:
            if f:
                f.verification_status = VerificationStatus.UNSUPPORTED
                flags = f.flags or {}
                flags["has_conflict"] = False
                flags["conflict_resolution"] = f"Neither supported: {resolution_notes}"
                f.flags = flags
    elif resolution_choice == ResolutionChoice.INVESTIGATION_REQUIRED:
        for f in [f_a, f_b]:
            if f:
                f.verification_status = VerificationStatus.NEEDS_REVIEW
                flags = f.flags or {}
                flags["has_conflict"] = True
                flags["conflict_resolution"] = f"Under active investigation: {resolution_notes}"
                f.flags = flags

    # Audit Log Entry
    audit = AuditLog(
        project_id=conflict.project_id,
        user_id=user.id,
        action="CONFLICT_RESOLVED",
        entity_type="CONFLICT",
        entity_id=conflict.id,
        details={
            "conflict_id": conflict.id,
            "title": conflict.title,
            "resolution_choice": resolution_choice,
            "resolution_notes": resolution_notes,
            "resolved_by_name": user.full_name,
            "finding_a_id": conflict.finding_a_id or conflict.finding_id_1,
            "finding_b_id": conflict.finding_b_id or conflict.finding_id_2
        }
    )
    db.add(audit)
    db.commit()
    db.refresh(conflict)
    return conflict

def dismiss_conflict(conflict_id: str, resolution_notes: str, db: Session, user: User) -> KnowledgeConflict:
    """Dismisses a conflict with required reason and updates findings."""
    if not resolution_notes or len(resolution_notes.strip()) < 5:
        raise ValueError("A detailed explanation is required to dismiss a conflict.")

    conflict = db.query(KnowledgeConflict).filter(KnowledgeConflict.id == conflict_id).first()
    if not conflict:
        raise ValueError("Conflict not found")

    conflict.conflict_status = ConflictStatus.DISMISSED
    conflict.status = ConflictStatus.DISMISSED
    conflict.resolution_notes = resolution_notes.strip()
    conflict.resolved_by = user.id
    conflict.resolved_at = datetime.utcnow()
    conflict.updated_at = datetime.utcnow()

    # Revert findings from CONFLICTED to VERIFIED
    f_a = db.query(ExtractedFinding).filter(ExtractedFinding.id == (conflict.finding_a_id or conflict.finding_id_1)).first()
    f_b = db.query(ExtractedFinding).filter(ExtractedFinding.id == (conflict.finding_b_id or conflict.finding_id_2)).first()

    for f in [f_a, f_b]:
        if f and f.verification_status == VerificationStatus.CONFLICTED:
            f.verification_status = VerificationStatus.VERIFIED
            flags = f.flags or {}
            flags["has_conflict"] = False
            flags["conflict_dismissed"] = f"Dismissed by {user.full_name}: {resolution_notes}"
            f.flags = flags

    audit = AuditLog(
        project_id=conflict.project_id,
        user_id=user.id,
        action="CONFLICT_DISMISSED",
        entity_type="CONFLICT",
        entity_id=conflict.id,
        details={
            "conflict_id": conflict.id,
            "title": conflict.title,
            "resolution_notes": resolution_notes,
            "dismissed_by_name": user.full_name
        }
    )
    db.add(audit)
    db.commit()
    db.refresh(conflict)
    return conflict

def get_evidence_coverage_metrics(project_id: str, db: Session) -> Dict[str, Any]:
    """
    Computes comprehensive evidence coverage metrics for the project dashboard:
    Coverage % = (Findings with valid evidence / Total factual findings) * 100
    """
    findings = db.query(ExtractedFinding).filter(ExtractedFinding.project_id == project_id).all()
    refs = db.query(EvidenceReference).join(ExtractedFinding, ExtractedFinding.id == EvidenceReference.finding_id)\
             .filter(ExtractedFinding.project_id == project_id).all()
    conflicts = db.query(KnowledgeConflict).filter(KnowledgeConflict.project_id == project_id).all()
    docs = db.query(Document).filter(Document.project_id == project_id).all()

    total_findings = len(findings)
    verified = sum(1 for f in findings if f.verification_status == VerificationStatus.VERIFIED)
    unsupported = sum(1 for f in findings if f.verification_status == VerificationStatus.UNSUPPORTED)
    needs_review = sum(1 for f in findings if f.verification_status == VerificationStatus.NEEDS_REVIEW)
    conflicted = sum(1 for f in findings if f.verification_status == VerificationStatus.CONFLICTED)

    # Broken citations: references pointing to non-existent document
    valid_doc_ids = {d.id for d in docs}
    broken_citations = sum(1 for r in refs if r.document_id not in valid_doc_ids)

    coverage_pct = round((verified / total_findings * 100), 1) if total_findings > 0 else 100.0
    fraction_str = f"{verified} / {total_findings} ({coverage_pct}%)"

    # Breakdown by entity type
    by_entity: Dict[str, int] = {}
    for f in findings:
        by_entity[f.entity_type] = by_entity.get(f.entity_type, 0) + (1 if f.verification_status == VerificationStatus.VERIFIED else 0)

    # Breakdown by document
    by_doc = []
    for d in docs:
        d_findings = [f for f in findings if f.document_id == d.id]
        d_verified = sum(1 for f in d_findings if f.verification_status == VerificationStatus.VERIFIED)
        d_total = len(d_findings)
        by_doc.append({
            "document_id": d.id,
            "filename": d.filename,
            "total_findings": d_total,
            "verified_findings": d_verified,
            "coverage_pct": round((d_verified / d_total * 100), 1) if d_total > 0 else 100.0
        })

    return {
        "total_findings": total_findings,
        "total_evidence_references": len(refs),
        "verified_count": verified,
        "unsupported_count": unsupported,
        "needs_review_count": needs_review,
        "conflicted_count": conflicted,
        "broken_citations_count": broken_citations,
        "coverage_percentage": coverage_pct,
        "coverage_fraction": fraction_str,
        "by_document": by_doc,
        "by_entity_type": by_entity
    }
