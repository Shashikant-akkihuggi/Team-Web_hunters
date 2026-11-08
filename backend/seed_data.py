import os
import shutil
from datetime import datetime, timedelta
from backend.app.database import SessionLocal, Base, engine
from backend.app.models import (
    User, UserRole, Project, ProjectMember, Document, DocumentChunk,
    ExtractedFinding, FindingStatus, Review, Handover, HandoverStatus, AuditLog
)
from backend.app.auth import get_password_hash
from backend.app.config import settings
from backend.app.services.document_parser import compute_file_hash, process_document
from backend.app.services.extraction_service import extract_project_knowledge
from backend.app.services.verification_service import run_project_verification
from backend.app.services.handover_service import generate_handover_report

def seed():
    print("--- Initializing database tables ---")
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    # Clear existing if needed or check if admin exists
    admin_user = db.query(User).filter(User.email == "admin@knowledgecontinuity.io").first()
    if admin_user:
        print("Database already seeded with admin user. Proceeding to verify/refresh.")
        db.close()
        return

    print("--- Creating Users ---")
    users_data = [
        ("admin@knowledgecontinuity.io", "Alexander Vance (Admin)", "Password123!", UserRole.ADMIN),
        ("pm@knowledgecontinuity.io", "Elena Rostova (Lead PM)", "Password123!", UserRole.PROJECT_MANAGER),
        ("outgoing@knowledgecontinuity.io", "Sarah Jenkins (Outgoing Lead)", "Password123!", UserRole.OUTGOING_MEMBER),
        ("incoming@knowledgecontinuity.io", "Marcus Chen (Incoming Engineer)", "Password123!", UserRole.INCOMING_MEMBER),
    ]

    users = {}
    for email, name, pwd, role in users_data:
        u = User(
            email=email,
            full_name=name,
            hashed_password=get_password_hash(pwd),
            role=role,
            is_active=True
        )
        db.add(u)
        db.commit()
        db.refresh(u)
        users[email] = u
        print(f"Created user: {email} [{role}]")

    print("--- Creating Project Apollo ---")
    apollo = Project(
        name="Project Apollo: Microservices & Data Ingestion",
        description="Core distributed event processing engine, analytical datastore migration, and payment gateway infrastructure.",
        domain="Core Platform Infrastructure",
        status="ACTIVE",
        target_handover_date=datetime.utcnow() + timedelta(days=21),
        handover_role="Senior Distributed Systems Engineer",
        created_by=users["pm@knowledgecontinuity.io"].id
    )
    db.add(apollo)
    db.commit()
    db.refresh(apollo)

    # Add Project Members
    for email, role in [
        ("admin@knowledgecontinuity.io", UserRole.ADMIN),
        ("pm@knowledgecontinuity.io", UserRole.PROJECT_MANAGER),
        ("outgoing@knowledgecontinuity.io", UserRole.OUTGOING_MEMBER),
        ("incoming@knowledgecontinuity.io", UserRole.INCOMING_MEMBER),
    ]:
        pm = ProjectMember(
            project_id=apollo.id,
            user_id=users[email].id,
            role=role
        )
        db.add(pm)
    db.commit()

    print("--- Ingesting Sample Documents ---")
    samples = [
        ("Apollo_Architecture_Decisions.pdf", "pdf"),
        ("Apollo_Handover_Notes.docx", "docx"),
        ("Sprint_24_Blockers_and_Risks.txt", "txt")
    ]

    project_dir = os.path.join(settings.UPLOAD_DIR, apollo.id)
    os.makedirs(project_dir, exist_ok=True)

    for fname, ftype in samples:
        src_path = os.path.join("sample_documents", fname)
        if not os.path.exists(src_path):
            continue

        with open(src_path, "rb") as f_in:
            content = f_in.read()

        dest_path = os.path.join(project_dir, fname)
        with open(dest_path, "wb") as f_out:
            f_out.write(content)

        page_count, chunks = process_document(dest_path, ftype)
        f_hash = compute_file_hash(content)

        doc = Document(
            project_id=apollo.id,
            filename=fname,
            file_path=dest_path,
            file_size=len(content),
            file_type=ftype,
            file_hash=f_hash,
            page_count=page_count,
            status="COMPLETED",
            uploaded_by=users["outgoing@knowledgecontinuity.io"].id
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)

        print(f"Ingested {fname} ({page_count} pages, {len(chunks)} chunks)")

        # Store chunks and extract
        for c in chunks:
            chunk = DocumentChunk(
                document_id=doc.id,
                project_id=apollo.id,
                page_number=c["page_number"],
                chunk_index=c["chunk_index"],
                text_content=c["text_content"],
                char_start=c["char_start"],
                char_end=c["char_end"]
            )
            db.add(chunk)

            # Extract entities
            findings = extract_project_knowledge(
                chunk_text=c["text_content"],
                page_number=c["page_number"],
                filename=fname
            )

            for f_dict in findings:
                finding = ExtractedFinding(
                    project_id=apollo.id,
                    document_id=doc.id,
                    entity_type=f_dict["entity_type"],
                    title=f_dict["title"],
                    description=f_dict["description"],
                    owner=f_dict["owner"],
                    deadline=f_dict["deadline"],
                    status=FindingStatus.DRAFT,
                    page_number=f_dict["page_number"],
                    supporting_quotation=f_dict["supporting_quotation"],
                    confidence_score=f_dict["confidence_score"],
                    is_recommendation=f_dict["is_recommendation"]
                )
                db.add(finding)

        db.commit()

    print("--- Running Evidence Verification & Conflict Detection ---")
    run_project_verification(apollo.id, db)

    print("--- Performing Managerial Human Reviews ---")
    all_findings = db.query(ExtractedFinding).filter(ExtractedFinding.project_id == apollo.id).all()
    
    # Approve non-conflicting findings
    for idx, f in enumerate(all_findings):
        if f.flags and f.flags.get("has_conflict"):
            # Mark for investigation
            f.status = FindingStatus.UNDER_INVESTIGATION
            rev = Review(
                finding_id=f.id,
                reviewer_id=users["pm@knowledgecontinuity.io"].id,
                action="FLAG_INVESTIGATION",
                comment="Conflicting deadlines identified between handover dossier (May 20) and Sprint 24 log (May 30). Needs engineering alignment.",
                previous_state={"status": "DRAFT"},
                new_state={"status": "UNDER_INVESTIGATION"}
            )
            db.add(rev)
        else:
            # Approve findings
            f.status = FindingStatus.APPROVED
            rev = Review(
                finding_id=f.id,
                reviewer_id=users["pm@knowledgecontinuity.io"].id,
                action="APPROVE",
                comment="Evidence verified against source page quotations. Approved for handover.",
                previous_state={"status": "DRAFT"},
                new_state={"status": "APPROVED"}
            )
            db.add(rev)
    db.commit()

    print("--- Generating & Approving Master Handover Report ---")
    handover_json = generate_handover_report(
        project_id=apollo.id,
        target_role=apollo.handover_role,
        user_id=users["pm@knowledgecontinuity.io"].id,
        db=db,
        custom_notes="Verified comprehensive handover for incoming Senior Distributed Systems Engineer."
    )

    handover = Handover(
        project_id=apollo.id,
        title=f"{apollo.name} - Official Handover Package",
        target_role=apollo.handover_role,
        status=HandoverStatus.APPROVED,
        summary=handover_json.get("project_overview", "")[:350],
        content_json=handover_json,
        generated_by=users["pm@knowledgecontinuity.io"].id,
        approved_by=users["pm@knowledgecontinuity.io"].id,
        approved_at=datetime.utcnow()
    )
    db.add(handover)

    # Final Audit Log
    audit = AuditLog(
        project_id=apollo.id,
        user_id=users["pm@knowledgecontinuity.io"].id,
        action="HANDOVER_FINALIZED_AND_APPROVED",
        entity_type="HANDOVER",
        entity_id=handover.id,
        details={"status": "APPROVED", "target_role": apollo.handover_role}
    )
    db.add(audit)
    db.commit()

    print("==================================================")
    print("SUCCESS: Knowledge Continuity seed data initialized!")
    print(f"Users created: {len(users_data)}")
    print(f"Documents: {len(samples)}")
    print(f"Findings extracted & verified: {len(all_findings)}")
    print(f"Master Handover ID: {handover.id}")
    print("==================================================")
    db.close()

if __name__ == "__main__":
    seed()
