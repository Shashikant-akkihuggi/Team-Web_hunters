import os
from datetime import datetime
from typing import List, Optional
from sqlalchemy.orm import Session

from backend.app.config import settings
from backend.app.models import (
    Document, DocumentChunk, DocumentPage, ExtractedFinding,
    ProcessingStatus, AuditLog, generate_uuid
)
from backend.app.services.storage_service import storage_service
from backend.app.services.document_parser import (
    parse_document,
    compute_file_hash,
    validate_file_signature,
    get_mime_type_for_ext,
    ParsedDocument,
    DocumentParserError,
    InsufficientTextError,
    UnsupportedFormatError
)
from backend.app.services.normalization_service import EmptyDocumentError
from backend.app.services.chunking_service import default_chunker
from backend.app.services.extraction_service import extract_project_knowledge
from backend.app.services.verification_service import run_project_verification

class DocumentPipelineError(Exception):
    pass

class DuplicateDocumentError(DocumentPipelineError):
    def __init__(self, message: str, existing_document_id: str):
        super().__init__(message)
        self.existing_document_id = existing_document_id

def process_single_document(
    file_bytes: bytes,
    original_filename: str,
    project_id: str,
    user_id: str,
    db: Session
) -> Document:
    """
    Executes the complete document ingestion and processing sequence:
    1. Validation (extension, size, signature)
    2. Deduplication check
    3. Storage persistence
    4. Database record creation (PROCESSING)
    5. Text parsing & OCR check
    6. Page-level extraction & storage
    7. Text chunking & storage
    8. Knowledge extraction integration
    9. Status finalization (PROCESSED or FAILED)
    """
    # 1. Validate file extension
    _, ext = os.path.splitext(original_filename)
    ext = ext.lower().strip()
    if ext not in settings.ALLOWED_EXTENSIONS:
        raise UnsupportedFormatError(
            f"Unsupported file format '{ext}' for file '{original_filename}'. Allowed: {', '.join(settings.ALLOWED_EXTENSIONS)}"
        )

    # 2. Validate file size
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if len(file_bytes) > max_bytes:
        raise DocumentPipelineError(
            f"File '{original_filename}' ({len(file_bytes)} bytes) exceeds the maximum allowed size of {settings.MAX_UPLOAD_SIZE_MB}MB."
        )

    # 3. Validate file signature / magic bytes
    if not validate_file_signature(file_bytes, ext):
        raise UnsupportedFormatError(
            f"File '{original_filename}' content signature does not match its '{ext}' file extension."
        )

    # 4. Compute cryptographic checksum
    f_hash = compute_file_hash(file_bytes)

    # 5. Deduplication check
    existing = db.query(Document).filter(
        Document.project_id == project_id,
        (Document.file_hash == f_hash) | (Document.checksum == f_hash)
    ).first()

    if existing and existing.status in [ProcessingStatus.PROCESSED, ProcessingStatus.COMPLETED, ProcessingStatus.PROCESSING]:
        raise DuplicateDocumentError(
            f"A document identical to '{original_filename}' has already been uploaded to this project (ID: {existing.id}).",
            existing_document_id=existing.id
        )

    # 6. Save original file securely in storage abstraction
    doc_id = generate_uuid()
    storage_key, abs_path = storage_service.save_file(
        project_id=project_id,
        document_id=doc_id,
        filename=original_filename,
        content=file_bytes
    )

    mime_type = get_mime_type_for_ext(ext)

    # 7. Create initial Document record in DB
    doc = Document(
        id=doc_id,
        project_id=project_id,
        filename=original_filename,
        original_filename=original_filename,
        file_path=abs_path,
        storage_key=storage_key,
        file_size=len(file_bytes),
        file_type=ext.replace(".", ""),
        mime_type=mime_type,
        file_extension=ext,
        file_hash=f_hash,
        checksum=f_hash,
        page_count=1,
        status=ProcessingStatus.PROCESSING,
        processing_status=ProcessingStatus.PROCESSING,
        extracted_character_count=0,
        chunk_count=0,
        error_message=None,
        processing_error=None,
        uploaded_by=user_id,
        created_at=datetime.utcnow()
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    # 8. Run Parsing and Chunking Pipeline
    try:
        parsed_doc = parse_document(abs_path, ext)

        # Store pages
        total_chars = 0
        for p in parsed_doc.pages:
            db_page = DocumentPage(
                document_id=doc.id,
                project_id=project_id,
                page_number=p.page_number,
                extracted_text=p.normalized_text,
                char_count=p.char_count,
                created_at=datetime.utcnow()
            )
            db.add(db_page)
            total_chars += p.char_count

        # Generate and store chunks
        chunks = default_chunker.chunk_document(parsed_doc)
        for c in chunks:
            db_chunk = DocumentChunk(
                document_id=doc.id,
                project_id=project_id,
                page_number=c.page_number,
                page_start=c.page_start,
                page_end=c.page_end,
                chunk_index=c.chunk_index,
                text_content=c.text_content,
                char_start=c.char_start,
                char_end=c.char_end,
                character_start=c.char_start,
                character_end=c.char_end,
                created_at=datetime.utcnow()
            )
            db.add(db_chunk)

            # Knowledge Extraction
            extracted_entities = extract_project_knowledge(
                chunk_text=c.text_content,
                page_number=c.page_number,
                filename=original_filename
            )
            for ent in extracted_entities:
                finding = ExtractedFinding(
                    project_id=project_id,
                    document_id=doc.id,
                    entity_type=ent["entity_type"],
                    title=ent["title"],
                    description=ent["description"],
                    owner=ent.get("owner"),
                    deadline=ent.get("deadline"),
                    status="DRAFT",
                    page_number=ent.get("page_number", c.page_number),
                    supporting_quotation=ent.get("supporting_quotation"),
                    confidence_score=ent.get("confidence_score", 1.0),
                    is_recommendation=ent.get("is_recommendation", False)
                )
                db.add(finding)

        # Update Document record to PROCESSED
        doc.page_count = parsed_doc.page_count
        doc.extracted_character_count = total_chars
        doc.chunk_count = len(chunks)
        doc.status = ProcessingStatus.PROCESSED
        doc.processing_status = ProcessingStatus.PROCESSED
        doc.processed_at = datetime.utcnow()
        doc.error_message = None
        doc.processing_error = None
        db.commit()
        db.refresh(doc)

        # Audit log
        audit = AuditLog(
            project_id=project_id,
            user_id=user_id,
            action="DOCUMENT_PROCESSED",
            entity_type="DOCUMENT",
            entity_id=doc.id,
            details={
                "filename": doc.filename,
                "pages": doc.page_count,
                "chunks": doc.chunk_count,
                "characters": doc.extracted_character_count
            }
        )
        db.add(audit)
        db.commit()

        # Re-run evidence verification
        try:
            run_project_verification(project_id, db)
        except Exception:
            pass

        return doc

    except Exception as e:
        db.rollback()
        # Clean any partial page or chunk records
        db.query(DocumentPage).filter(DocumentPage.document_id == doc.id).delete()
        db.query(DocumentChunk).filter(DocumentChunk.document_id == doc.id).delete()
        db.query(ExtractedFinding).filter(ExtractedFinding.document_id == doc.id).delete()

        # Mark Document as FAILED with error explanation
        doc.status = ProcessingStatus.FAILED
        doc.processing_status = ProcessingStatus.FAILED
        doc.error_message = str(e)
        doc.processing_error = str(e)
        doc.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(doc)

        # Audit log for failure
        audit = AuditLog(
            project_id=project_id,
            user_id=user_id,
            action="DOCUMENT_PROCESSING_FAILED",
            entity_type="DOCUMENT",
            entity_id=doc.id,
            details={"filename": doc.filename, "error": str(e)}
        )
        db.add(audit)
        db.commit()

        return doc

def retry_document_processing(document_id: str, db: Session, user_id: str) -> Document:
    """
    Retries parsing and chunking for a failed document.
    Re-reads from the secured storage file.
    """
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise DocumentPipelineError(f"Document '{document_id}' not found.")

    if not os.path.exists(doc.file_path):
        raise DocumentPipelineError("Original source file is missing from storage and cannot be reprocessed.")

    # Reset state to PROCESSING
    doc.status = ProcessingStatus.PROCESSING
    doc.processing_status = ProcessingStatus.PROCESSING
    doc.error_message = None
    doc.processing_error = None
    db.commit()

    # Clear stale pages and chunks
    db.query(DocumentPage).filter(DocumentPage.document_id == doc.id).delete()
    db.query(DocumentChunk).filter(DocumentChunk.document_id == doc.id).delete()
    db.query(ExtractedFinding).filter(ExtractedFinding.document_id == doc.id).delete()
    db.commit()

    try:
        _, ext = os.path.splitext(doc.filename)
        parsed_doc = parse_document(doc.file_path, ext)

        total_chars = 0
        for p in parsed_doc.pages:
            db_page = DocumentPage(
                document_id=doc.id,
                project_id=doc.project_id,
                page_number=p.page_number,
                extracted_text=p.normalized_text,
                char_count=p.char_count,
                created_at=datetime.utcnow()
            )
            db.add(db_page)
            total_chars += p.char_count

        chunks = default_chunker.chunk_document(parsed_doc)
        for c in chunks:
            db_chunk = DocumentChunk(
                document_id=doc.id,
                project_id=doc.project_id,
                page_number=c.page_number,
                page_start=c.page_start,
                page_end=c.page_end,
                chunk_index=c.chunk_index,
                text_content=c.text_content,
                char_start=c.char_start,
                char_end=c.char_end,
                character_start=c.char_start,
                character_end=c.char_end,
                created_at=datetime.utcnow()
            )
            db.add(db_chunk)

            # Knowledge Extraction
            extracted_entities = extract_project_knowledge(
                chunk_text=c.text_content,
                page_number=c.page_number,
                filename=doc.filename
            )
            for ent in extracted_entities:
                finding = ExtractedFinding(
                    project_id=doc.project_id,
                    document_id=doc.id,
                    entity_type=ent["entity_type"],
                    title=ent["title"],
                    description=ent["description"],
                    owner=ent.get("owner"),
                    deadline=ent.get("deadline"),
                    status="DRAFT",
                    page_number=ent.get("page_number", c.page_number),
                    supporting_quotation=ent.get("supporting_quotation"),
                    confidence_score=ent.get("confidence_score", 1.0),
                    is_recommendation=ent.get("is_recommendation", False)
                )
                db.add(finding)

        doc.page_count = parsed_doc.page_count
        doc.extracted_character_count = total_chars
        doc.chunk_count = len(chunks)
        doc.status = ProcessingStatus.PROCESSED
        doc.processing_status = ProcessingStatus.PROCESSED
        doc.processed_at = datetime.utcnow()
        doc.error_message = None
        doc.processing_error = None
        db.commit()
        db.refresh(doc)

        audit = AuditLog(
            project_id=doc.project_id,
            user_id=user_id,
            action="DOCUMENT_RETRY_SUCCESS",
            entity_type="DOCUMENT",
            entity_id=doc.id,
            details={"filename": doc.filename, "chunks": doc.chunk_count}
        )
        db.add(audit)
        db.commit()

        try:
            run_project_verification(doc.project_id, db)
        except Exception:
            pass

        return doc

    except Exception as e:
        db.rollback()
        db.query(DocumentPage).filter(DocumentPage.document_id == doc.id).delete()
        db.query(DocumentChunk).filter(DocumentChunk.document_id == doc.id).delete()
        db.query(ExtractedFinding).filter(ExtractedFinding.document_id == doc.id).delete()

        doc.status = ProcessingStatus.FAILED
        doc.processing_status = ProcessingStatus.FAILED
        doc.error_message = str(e)
        doc.processing_error = str(e)
        db.commit()
        db.refresh(doc)
        return doc
