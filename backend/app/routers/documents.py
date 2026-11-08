import os
import shutil
from typing import List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.config import settings
from backend.app.models import Document, DocumentChunk, ExtractedFinding, User, UserRole, AuditLog
from backend.app.schemas import DocumentResponse, DocumentChunkResponse
from backend.app.auth import get_current_user, check_project_access
from backend.app.services.document_parser import compute_file_hash, process_document
from backend.app.services.extraction_service import extract_project_knowledge
from backend.app.services.verification_service import run_project_verification

router = APIRouter(prefix="/documents", tags=["Documents"])

@router.post("/{project_id}/upload", response_model=List[DocumentResponse])
async def upload_documents(
    project_id: str,
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # OUTGOING_MEMBER, PROJECT_MANAGER, and ADMIN can upload documents
    check_project_access(project_id, current_user, db, allowed_roles=[UserRole.ADMIN, UserRole.PROJECT_MANAGER, UserRole.OUTGOING_MEMBER])

    uploaded_docs = []

    for file in files:
        # Validate extension
        _, ext = os.path.splitext(file.filename)
        ext = ext.lower()
        if ext not in settings.ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported file format '{ext}' for file {file.filename}. Allowed: {', '.join(settings.ALLOWED_EXTENSIONS)}"
            )

        content = await file.read()
        if len(content) > settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File {file.filename} exceeds {settings.MAX_UPLOAD_SIZE_MB}MB limit."
            )

        # Hash check for duplicate
        f_hash = compute_file_hash(content)
        existing_doc = db.query(Document).filter(
            Document.project_id == project_id,
            Document.file_hash == f_hash
        ).first()

        if existing_doc:
            # Skip or notify duplicate
            continue

        # Save to disk
        project_upload_dir = os.path.join(settings.UPLOAD_DIR, project_id)
        os.makedirs(project_upload_dir, exist_ok=True)
        safe_filename = f"{f_hash[:12]}_{file.filename}"
        saved_path = os.path.join(project_upload_dir, safe_filename)

        with open(saved_path, "wb") as f_out:
            f_out.write(content)

        # Parse text into page-level chunks
        try:
            page_count, chunks_data = process_document(saved_path, ext)
            doc_status = "COMPLETED"
            err_msg = None
        except Exception as e:
            page_count = 1
            chunks_data = []
            doc_status = "FAILED"
            err_msg = str(e)

        # Create Document record
        doc = Document(
            project_id=project_id,
            filename=file.filename,
            file_path=saved_path,
            file_size=len(content),
            file_type=ext.replace(".", ""),
            file_hash=f_hash,
            page_count=page_count,
            status=doc_status,
            error_message=err_msg,
            uploaded_by=current_user.id
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)

        # Store chunks and run extraction
        if doc_status == "COMPLETED" and chunks_data:
            for c in chunks_data:
                chunk = DocumentChunk(
                    document_id=doc.id,
                    project_id=project_id,
                    page_number=c["page_number"],
                    chunk_index=c["chunk_index"],
                    text_content=c["text_content"],
                    char_start=c["char_start"],
                    char_end=c["char_end"]
                )
                db.add(chunk)

                # Extract entities from chunk
                extracted_entities = extract_project_knowledge(
                    chunk_text=c["text_content"],
                    page_number=c["page_number"],
                    filename=file.filename
                )

                for ent in extracted_entities:
                    finding = ExtractedFinding(
                        project_id=project_id,
                        document_id=doc.id,
                        entity_type=ent["entity_type"],
                        title=ent["title"],
                        description=ent["description"],
                        owner=ent["owner"],
                        deadline=ent["deadline"],
                        status="DRAFT",
                        page_number=ent["page_number"],
                        supporting_quotation=ent["supporting_quotation"],
                        confidence_score=ent["confidence_score"],
                        is_recommendation=ent["is_recommendation"]
                    )
                    db.add(finding)

            db.commit()

        # Audit log
        audit = AuditLog(
            project_id=project_id,
            user_id=current_user.id,
            action="DOCUMENT_UPLOADED",
            entity_type="DOCUMENT",
            entity_id=doc.id,
            details={"filename": doc.filename, "pages": page_count, "chunks": len(chunks_data)}
        )
        db.add(audit)
        db.commit()

        uploaded_docs.append(DocumentResponse(
            id=doc.id,
            project_id=doc.project_id,
            filename=doc.filename,
            file_size=doc.file_size,
            file_type=doc.file_type,
            file_hash=doc.file_hash,
            page_count=doc.page_count,
            status=doc.status,
            error_message=doc.error_message,
            uploaded_by=doc.uploaded_by,
            created_at=doc.created_at,
            chunks_count=len(chunks_data)
        ))

    # Run evidence verification and conflict detection across all project findings
    if uploaded_docs:
        run_project_verification(project_id, db)

    return uploaded_docs

@router.get("/{project_id}", response_model=List[DocumentResponse])
def list_documents(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    check_project_access(project_id, current_user, db)
    docs = db.query(Document).filter(Document.project_id == project_id).order_by(Document.created_at.desc()).all()
    results = []
    for d in docs:
        c_count = db.query(DocumentChunk).filter(DocumentChunk.document_id == d.id).count()
        results.append(DocumentResponse(
            id=d.id,
            project_id=d.project_id,
            filename=d.filename,
            file_size=d.file_size,
            file_type=d.file_type,
            file_hash=d.file_hash,
            page_count=d.page_count,
            status=d.status,
            error_message=d.error_message,
            uploaded_by=d.uploaded_by,
            created_at=d.created_at,
            chunks_count=c_count
        ))
    return results

@router.get("/{project_id}/{document_id}/chunks", response_model=List[DocumentChunkResponse])
def get_document_chunks(
    project_id: str,
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    check_project_access(project_id, current_user, db)
    chunks = (
        db.query(DocumentChunk)
        .filter(DocumentChunk.project_id == project_id, DocumentChunk.document_id == document_id)
        .order_by(DocumentChunk.page_number.asc(), DocumentChunk.chunk_index.asc())
        .all()
    )
    return chunks

@router.delete("/{project_id}/{document_id}")
def delete_document(
    project_id: str,
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    check_project_access(project_id, current_user, db, allowed_roles=[UserRole.ADMIN, UserRole.PROJECT_MANAGER])
    doc = db.query(Document).filter(Document.id == document_id, Document.project_id == project_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Delete physical file if exists
    if os.path.exists(doc.file_path):
        try:
            os.remove(doc.file_path)
        except Exception:
            pass

    db.delete(doc)
    audit = AuditLog(
        project_id=project_id,
        user_id=current_user.id,
        action="DOCUMENT_DELETED",
        entity_type="DOCUMENT",
        entity_id=document_id,
        details={"filename": doc.filename}
    )
    db.add(audit)
    db.commit()

    # Re-run verification to clear stale citations
    run_project_verification(project_id, db)
    return {"message": "Document deleted successfully"}
