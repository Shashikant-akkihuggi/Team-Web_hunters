import re
from typing import List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from difflib import SequenceMatcher

from backend.app.models import ExtractedFinding, DocumentChunk, EvidenceReference, VerificationStatus

def normalize_text(text: str) -> str:
    """Normalize text by collapsing whitespace and lowercasing."""
    return re.sub(r'\s+', ' ', text).strip().lower()

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
    quote_tokens = set(norm_quote.split())
    chunk_tokens = set(norm_chunk.split())
    if not quote_tokens:
        return 0.0
    overlap = len(quote_tokens.intersection(chunk_tokens)) / len(quote_tokens)

    # 3. SequenceMatcher for approximate fuzzy alignment
    if len(norm_quote) < 300:
        seq_ratio = SequenceMatcher(None, norm_quote, norm_chunk).quick_ratio()
        return max(overlap * 0.9, seq_ratio)

    return overlap

def verify_single_finding(
    finding: ExtractedFinding,
    chunks: List[DocumentChunk]
) -> Tuple[bool, float, int]:
    """
    Verifies that the finding's supporting_quotation exists in one of the document chunks.
    Prioritizes the designated page_number.
    Returns (is_verified, best_score, verified_page).
    """
    quote = finding.supporting_quotation
    if not quote or len(quote.strip()) < 10:
        return False, 0.0, finding.page_number or 1

    best_score = 0.0
    best_page = finding.page_number or 1

    # First check chunks matching the claimed page number
    target_chunks = [c for c in chunks if c.page_number == finding.page_number]
    other_chunks = [c for c in chunks if c.page_number != finding.page_number]

    for chunk in target_chunks:
        score = calculate_match_score(quote, chunk.text_content)
        if score > best_score:
            best_score = score
            best_page = chunk.page_number
            if best_score >= 0.99:
                break

    # If not found on claimed page, inspect other pages
    if best_score < 0.8:
        for chunk in other_chunks:
            score = calculate_match_score(quote, chunk.text_content)
            if score > best_score:
                best_score = score
                best_page = chunk.page_number
                if best_score >= 0.99:
                    break

    is_verified = (best_score >= 0.70)
    return is_verified, round(best_score, 2), best_page

def run_project_verification(project_id: str, db: Session):
    """
    Runs evidence verification across all findings in a project.
    Generates EvidenceReference records, detects conflicting dates/owners, and flags anomalies.
    """
    findings = db.query(ExtractedFinding).filter(ExtractedFinding.project_id == project_id).all()
    chunks = db.query(DocumentChunk).filter(DocumentChunk.project_id == project_id).all()

    # Group chunks by document_id
    chunks_by_doc: Dict[str, List[DocumentChunk]] = {}
    for c in chunks:
        chunks_by_doc.setdefault(c.document_id, []).append(c)

    # 1. Evidence Citation Verification
    for f in findings:
        doc_chunks = chunks_by_doc.get(f.document_id, [])
        is_verified, score, verified_page = verify_single_finding(f, doc_chunks)

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
        else:
            flags["missing_evidence"] = False
            flags["evidence_strength"] = "STRONG"
            f.verification_status = VerificationStatus.VERIFIED

        # Check ambiguous ownership
        if f.owner and (" or " in f.owner.lower() or "unclear" in f.owner.lower() or "tbd" in f.owner.lower()):
            flags["ambiguous_ownership"] = True
        else:
            flags["ambiguous_ownership"] = False

        f.flags = flags

    # 2. Cross-Finding Conflict Detection
    # Detect contradictory deadlines or owners for similar topics
    for i, f1 in enumerate(findings):
        for f2 in findings[i+1:]:
            # Compare similarity of titles/descriptions
            title_sim = SequenceMatcher(None, normalize_text(f1.title), normalize_text(f2.title)).ratio()
            if title_sim > 0.65 or (f1.entity_type == f2.entity_type and f1.entity_type in ["DEADLINE", "TASK", "MILESTONE"]):
                # Check deadline conflict
                if f1.deadline and f2.deadline and f1.deadline.strip().lower() != f2.deadline.strip().lower():
                    flags1 = f1.flags or {}
                    flags2 = f2.flags or {}
                    flags1["has_conflict"] = True
                    flags1["conflict_reason"] = f"Contradictory deadline '{f1.deadline}' vs '{f2.deadline}' in finding '{f2.title[:40]}'"
                    flags2["has_conflict"] = True
                    flags2["conflict_reason"] = f"Contradictory deadline '{f2.deadline}' vs '{f1.deadline}' in finding '{f1.title[:40]}'"
                    f1.flags = flags1
                    f2.flags = flags2
                    f1.verification_status = VerificationStatus.CONFLICTING
                    f2.verification_status = VerificationStatus.CONFLICTING

                # Check owner conflict for the same task
                if f1.entity_type == "TASK" and f1.owner and f2.owner and f1.owner.strip().lower() != f2.owner.strip().lower() and title_sim > 0.65:
                    flags1 = f1.flags or {}
                    flags2 = f2.flags or {}
                    flags1["ambiguous_ownership"] = True
                    flags1["ownership_conflict"] = f"Contradicting owner '{f1.owner}' vs '{f2.owner}'"
                    flags2["ambiguous_ownership"] = True
                    flags2["ownership_conflict"] = f"Contradicting owner '{f2.owner}' vs '{f1.owner}'"
                    f1.flags = flags1
                    f2.flags = flags2

    db.commit()
