import logging
import re
from typing import List, Dict, Any, Tuple, Optional
from sqlalchemy.orm import Session
from difflib import SequenceMatcher

from backend.app.models import (
    ExtractedFinding, DocumentChunk, EvidenceReference,
    VerificationStatus, KnowledgeConflict, ConflictType, ConflictStatus
)

logger = logging.getLogger(__name__)

def normalize_text(text: str) -> str:
    """Normalize text by collapsing whitespace and lowercasing."""
    if not text:
        return ""
    return re.sub(r'\s+', ' ', text).strip().lower()

def extract_core_topic(title: str) -> str:
    """Extracts base topic words stripping prefix labels like 'Task:', 'Decision:', 'Blocked Task:'."""
    clean = re.sub(r'^(?:task|decision|risk|blocker|dependency|question|milestone|blocked task):\s*', '', title, flags=re.IGNORECASE)
    return clean.strip().lower()

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

def are_topics_conflicting(t1: str, t2: str) -> bool:
    """Checks if two titles / topics refer to the same project entity."""
    c1 = extract_core_topic(t1)
    c2 = extract_core_topic(t2)
    if c1 in c2 or c2 in c1:
        return True
    sim = SequenceMatcher(None, c1, c2).ratio()
    return sim > 0.60

def run_project_verification(project_id: str, db: Session) -> Dict[str, int]:
    """
    Runs comprehensive evidence verification, contradiction detection, and deduplication
    across all findings in a project.
    Generates EvidenceReference and KnowledgeConflict records.
    Returns summary statistics.
    """
    findings = db.query(ExtractedFinding).filter(ExtractedFinding.project_id == project_id).all()
    chunks = db.query(DocumentChunk).filter(DocumentChunk.project_id == project_id).all()

    # Group chunks by document_id
    chunks_by_doc: Dict[str, List[DocumentChunk]] = {}
    for c in chunks:
        chunks_by_doc.setdefault(c.document_id, []).append(c)

    verified_count = 0
    unsupported_count = 0
    conflicts_detected = 0

    # 1. Evidence Citation Verification
    for f in findings:
        doc_chunks = chunks_by_doc.get(f.document_id, [])
        is_verified, score, verified_page, verified_chunk_id = verify_single_finding(f, doc_chunks)

        if verified_chunk_id and not f.chunk_id:
            f.chunk_id = verified_chunk_id

        # Update or create EvidenceReference
        existing_ref = db.query(EvidenceReference).filter(EvidenceReference.finding_id == f.id).first()
        if existing_ref:
            existing_ref.quotation = f.supporting_quotation or ""
            existing_ref.page_number = verified_page
            existing_ref.match_score = score
            existing_ref.is_verified = is_verified
        else:
            new_ref = EvidenceReference(
                finding_id=f.id,
                document_id=f.document_id or (doc_chunks[0].document_id if doc_chunks else "unknown"),
                page_number=verified_page,
                quotation=f.supporting_quotation or "",
                match_score=score,
                is_verified=is_verified
            )
            db.add(new_ref)

        flags = f.flags or {}
        if not is_verified:
            flags["missing_evidence"] = True
            flags["evidence_strength"] = "NONE" if score == 0.0 else "WEAK"
            f.verification_status = VerificationStatus.UNSUPPORTED
            unsupported_count += 1
        else:
            flags["missing_evidence"] = False
            flags["evidence_strength"] = "STRONG"
            f.verification_status = VerificationStatus.VERIFIED
            verified_count += 1

        # Check ambiguous ownership
        if f.owner and (" or " in f.owner.lower() or "unclear" in f.owner.lower() or "tbd" in f.owner.lower()):
            flags["ambiguous_ownership"] = True
        else:
            flags["ambiguous_ownership"] = False

        f.flags = flags

    # 2. Contradiction Detection Engine
    # Clear existing conflicts for clean re-computation
    db.query(KnowledgeConflict).filter(KnowledgeConflict.project_id == project_id).delete()

    for i, f1 in enumerate(findings):
        for f2 in findings[i+1:]:
            same_entity_family = (f1.entity_type == f2.entity_type) or (
                f1.entity_type in ["TASK", "BLOCKER"] and f2.entity_type in ["TASK", "BLOCKER"]
            )
            if not same_entity_family:
                continue

            topic_match = are_topics_conflicting(f1.title, f2.title) or are_topics_conflicting(f1.description, f2.description)
            if not topic_match:
                continue

            conflict_type = None
            conflict_desc = None

            # A. Task Status Contradiction
            # e.g., COMPLETED vs BLOCKED, or IN_PROGRESS vs BLOCKED, or COMPLETED vs IN_PROGRESS
            s1 = (f1.task_status or f1.status or "").upper()
            s2 = (f2.task_status or f2.status or "").upper()
            if s1 and s2 and s1 != s2:
                # Contradicting statuses
                if {"COMPLETED", "BLOCKED"}.issubset({s1, s2}) or \
                   {"IN_PROGRESS", "BLOCKED"}.issubset({s1, s2}) or \
                   {"COMPLETED", "IN_PROGRESS"}.issubset({s1, s2}) or \
                   {"COMPLETED", "NOT_STARTED"}.issubset({s1, s2}):
                    conflict_type = ConflictType.STATUS
                    conflict_desc = f"Conflicting status for '{f1.title}': '{s1}' vs '{s2}' across documents."

            # B. Deadline Contradiction
            if not conflict_type and f1.deadline and f2.deadline and f1.deadline.strip().lower() != f2.deadline.strip().lower():
                conflict_type = ConflictType.DEADLINE
                conflict_desc = f"Contradictory delivery deadline for '{f1.title}': '{f1.deadline}' vs '{f2.deadline}'."

            # C. Ownership Contradiction
            if not conflict_type and f1.owner and f2.owner and f1.owner.strip().lower() != f2.owner.strip().lower():
                conflict_type = ConflictType.OWNERSHIP
                conflict_desc = f"Contradicting assigned owner for '{f1.title}': '{f1.owner}' vs '{f2.owner}'."

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

                # Create persistent KnowledgeConflict record
                conflict_record = KnowledgeConflict(
                    project_id=project_id,
                    finding_id_1=f1.id,
                    finding_id_2=f2.id,
                    conflict_type=conflict_type,
                    description=conflict_desc,
                    source_1_quote=f1.supporting_quotation,
                    source_1_page=f1.page_number,
                    source_1_doc_id=f1.document_id,
                    source_2_quote=f2.supporting_quotation,
                    source_2_page=f2.page_number,
                    source_2_doc_id=f2.document_id,
                    status=ConflictStatus.OPEN
                )
                db.add(conflict_record)

    db.commit()

    return {
        "total_findings": len(findings),
        "verified_count": verified_count,
        "unsupported_count": unsupported_count,
        "conflicts_count": conflicts_detected
    }
