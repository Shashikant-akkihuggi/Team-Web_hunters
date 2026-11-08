import os
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.config import settings
from backend.app.models import (
    Document, DocumentChunk, DocumentPage, ExtractedFinding,
    User, UserRole, AuditLog, ProcessingStatus
)
from backend.app.schemas import (
    DocumentResponse, DocumentChunkResponse,
    DocumentContentResponse, DocumentPageResponse, DocumentStatusResponse
)
from backend.app.auth import get_current_user, check_project_access
from backend.app.services.document_pipeline import (
    process_single_document,
    retry_document_processing,
    DuplicateDocumentError,
    DocumentPipelineError,
    UnsupportedFormatError
)
from backend.app.services.storage_service import storage_service
from backend.app.services.verification_service import run_project_verification

router = APIRouter(prefix="/documents", tags=["Documents"])

def serialize_document(doc: Document, db: Session) -> DocumentResponse:
    """Serializes a Document model to DocumentResponse with fresh chunk counts."""
    chunk_count = db.query(DocumentChunk).filter(DocumentChunk.document_id == doc.id).count()
    return DocumentResponse(
        id=doc.id,
        project_id=doc.project_id,
        filename=doc.filename,
        original_filename=doc.original_filename or doc.filename,
        storage_key=doc.storage_key,
        file_size=doc.file_size,
        file_type=doc.file_type,
        mime_type=doc.mime_type,
        file_extension=doc.file_extension or f".{doc.file_type}",
        file_hash=doc.file_hash,
        checksum=doc.checksum or doc.file_hash,
        page_count=doc.page_count,
        status=doc.status,
        processing_status=doc.processing_status or doc.status,
        extracted_character_count=doc.extracted_character_count or 0,
        chunk_count=chunk_count,
        chunks_count=chunk_count,
        error_message=doc.error_message,
        processing_error=doc.processing_error or doc.error_message,
        uploaded_by=doc.uploaded_by,
        created_at=doc.created_at,
        updated_at=doc.updated_at,
        processed_at=doc.processed_at
    )

@router.post("/{project_id}/upload", response_model=List[DocumentResponse])
async def upload_documents(
    project_id: str,
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Upload and ingest multiple documents into a project.
    Enforces format, magic byte signature, and 25MB size validation.
    Permitted roles: ADMIN, PROJECT_MANAGER, OUTGOING_MEMBER.
    """
    check_project_access(
        project_id, current_user, db,
        allowed_roles=[UserRole.ADMIN, UserRole.PROJECT_MANAGER, UserRole.OUTGOING_MEMBER]
    )

    if not files:
        raise HTTPException(status_code=400, detail="No files provided for upload.")

    uploaded_docs: List[DocumentResponse] = []
    errors: List[str] = []

    for file in files:
        content = await file.read()
        try:
            doc = process_single_document(
                file_bytes=content,
                original_filename=file.filename or "unnamed_document",
                project_id=project_id,
                user_id=current_user.id,
                db=db
            )
            uploaded_docs.append(serialize_document(doc, db))
        except DuplicateDocumentError as e:
            # If duplicate, retrieve existing document so client can see it
            existing_doc = db.query(Document).filter(Document.id == e.existing_document_id).first()
            if existing_doc:
                uploaded_docs.append(serialize_document(existing_doc, db))
        except (UnsupportedFormatError, DocumentPipelineError) as e:
            errors.append(f"{file.filename}: {str(e)}")
        except Exception as e:
            errors.append(f"{file.filename}: Unexpected processing error ({str(e)})")

    if not uploaded_docs and errors:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="; ".join(errors)
        )

    return uploaded_docs

@router.get("/{project_id}", response_model=List[DocumentResponse])
def list_project_documents(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all documents for an authorized project workspace."""
    check_project_access(project_id, current_user, db)
    docs = db.query(Document).filter(Document.project_id == project_id).order_by(Document.created_at.desc()).all()
    return [serialize_document(d, db) for d in docs]

# Backward compatibility alias
list_documents = list_project_documents

@router.get("/detail/{document_id}", response_model=DocumentResponse)
@router.get("/item/{document_id}", response_model=DocumentResponse)
def get_document_by_id(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retrieve metadata and processing metrics for a single document."""
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail=f"Document '{document_id}' not found.")
    check_project_access(doc.project_id, current_user, db)
    return serialize_document(doc, db)

@router.get("/{document_id}/status", response_model=DocumentStatusResponse)
def get_document_status(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Fetch real-time processing status, statistics, and error information."""
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")
    check_project_access(doc.project_id, current_user, db)

    chunk_count = db.query(DocumentChunk).filter(DocumentChunk.document_id == doc.id).count()
    return DocumentStatusResponse(
        id=doc.id,
        filename=doc.filename,
        status=doc.status,
        processing_status=doc.processing_status or doc.status,
        page_count=doc.page_count,
        chunk_count=chunk_count,
        extracted_character_count=doc.extracted_character_count or 0,
        error_message=doc.error_message,
        processing_error=doc.processing_error or doc.error_message,
        processed_at=doc.processed_at
    )

@router.get("/{document_id}/content", response_model=DocumentContentResponse)
def get_document_content(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retrieve original extracted full text and page-by-page text.
    Enforces project-level permission checks.
    """
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")
    check_project_access(doc.project_id, current_user, db)

    # 1. Query stored pages
    pages = (
        db.query(DocumentPage)
        .filter(DocumentPage.document_id == doc.id)
        .order_by(DocumentPage.page_number.asc())
        .all()
    )

    if pages:
        full_text = "\n\n".join(p.extracted_text for p in pages)
        page_responses = [
            DocumentPageResponse(
                id=p.id,
                document_id=p.document_id,
                page_number=p.page_number,
                extracted_text=p.extracted_text,
                char_count=p.char_count,
                created_at=p.created_at
            )
            for p in pages
        ]
    else:
        # Fallback to chunks if legacy document
        chunks = (
            db.query(DocumentChunk)
            .filter(DocumentChunk.document_id == doc.id)
            .order_by(DocumentChunk.chunk_index.asc())
            .all()
        )
        full_text = "\n\n".join(c.text_content for c in chunks)
        page_responses = []

    return DocumentContentResponse(
        id=doc.id,
        filename=doc.filename,
        page_count=doc.page_count,
        extracted_character_count=len(full_text),
        full_text=full_text,
        pages=page_responses
    )

@router.get("/{document_id}/chunks", response_model=List[DocumentChunkResponse])
@router.get("/{project_id}/{document_id}/chunks", response_model=List[DocumentChunkResponse])
def get_document_chunks(
    document_id: str,
    project_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Fetch all generated chunks for a document with page and character offsets."""
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")
    check_project_access(doc.project_id, current_user, db)

    chunks = (
        db.query(DocumentChunk)
        .filter(DocumentChunk.document_id == document_id)
        .order_by(DocumentChunk.page_number.asc(), DocumentChunk.chunk_index.asc())
        .all()
    )

    return [
        DocumentChunkResponse(
            id=c.id,
            document_id=c.document_id,
            project_id=c.project_id,
            page_number=c.page_number,
            page_start=c.page_start or c.page_number,
            page_end=c.page_end or c.page_number,
            chunk_index=c.chunk_index,
            text_content=c.text_content,
            content=c.text_content,
            char_start=c.char_start,
            char_end=c.char_end,
            character_start=c.character_start or c.char_start,
            character_end=c.character_end or c.char_end,
            created_at=c.created_at
        )
        for c in chunks
    ]

@router.post("/{document_id}/retry", response_model=DocumentResponse)
def retry_failed_document(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retry parsing and chunking for a failed document.
    Permitted for ADMIN, PROJECT_MANAGER, and OUTGOING_MEMBER.
    """
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")
    check_project_access(
        doc.project_id, current_user, db,
        allowed_roles=[UserRole.ADMIN, UserRole.PROJECT_MANAGER, UserRole.OUTGOING_MEMBER]
    )

    try:
        updated_doc = retry_document_processing(document_id, db, current_user.id)
        return serialize_document(updated_doc, db)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/{document_id}")
@router.delete("/{project_id}/{document_id}")
def delete_document(
    document_id: str,
    project_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete a document and its storage file, chunks, pages, and findings.
    Permitted ONLY for ADMIN and PROJECT_MANAGER.
    """
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")

    check_project_access(
        doc.project_id, current_user, db,
        allowed_roles=[UserRole.ADMIN, UserRole.PROJECT_MANAGER]
    )

    proj_id = doc.project_id
    filename = doc.filename

    # Delete storage file
    if doc.storage_key:
        storage_service.delete_file(doc.storage_key)
    elif doc.file_path and os.path.exists(doc.file_path):
        try:
            os.remove(doc.file_path)
        except Exception:
            pass

    db.delete(doc)

    audit = AuditLog(
        project_id=proj_id,
        user_id=current_user.id,
        action="DOCUMENT_DELETED",
        entity_type="DOCUMENT",
        entity_id=document_id,
        details={"filename": filename}
    )
    db.add(audit)
    db.commit()

    # Re-run verification to clear stale citations
    try:
        run_project_verification(proj_id, db)
    except Exception:
        pass

    return {"message": f"Document '{filename}' deleted successfully."}
