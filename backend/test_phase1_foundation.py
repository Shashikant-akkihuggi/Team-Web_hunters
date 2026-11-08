import os
import sys
from sqlalchemy import text
from fastapi import HTTPException

# Ensure root directory is on python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.app.main import health_check, root
from backend.app.database import engine, SessionLocal
from backend.app.models import (
    User, Project, ProjectMember, Document, DocumentChunk,
    ExtractedFinding, EvidenceReference, Handover, Review, AuditLog
)
from backend.app.routers.auth import login
from backend.app.routers.users import list_users
from backend.app.routers.projects import list_projects
from backend.app.routers.documents import list_documents
from backend.app.routers.extraction import get_extraction_status
from backend.app.routers.knowledge import list_findings
from backend.app.routers.evidence import get_finding_evidence
from backend.app.routers.handovers import list_handovers
from backend.app.routers.permissions import get_permissions_matrix, get_my_permissions
from backend.app.routers.review import get_review_queue
from backend.app.schemas import UserLogin

def test_database_connection():
    """Verify database connection and all 10 tables exist."""
    print("\n[TEST 1] Testing Database Connection and Table Schema...")
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1")).scalar()
        assert result == 1, "Database query failed"

    db = SessionLocal()
    try:
        user_count = db.query(User).count()
        proj_count = db.query(Project).count()
        pm_count = db.query(ProjectMember).count()
        doc_count = db.query(Document).count()
        chunk_count = db.query(DocumentChunk).count()
        finding_count = db.query(ExtractedFinding).count()
        ev_count = db.query(EvidenceReference).count()
        handover_count = db.query(Handover).count()
        review_count = db.query(Review).count()
        audit_count = db.query(AuditLog).count()

        assert user_count >= 4, "Users should be seeded"
        assert proj_count >= 1, "At least one project should be seeded"
        assert doc_count >= 3, "At least 3 documents should be seeded"
        assert finding_count >= 20, "Findings should be extracted"

        print(f"  -> Database Tables verified successfully.")
        print(f"     Users: {user_count}, Projects: {proj_count}, Members: {pm_count}")
        print(f"     Docs: {doc_count}, Chunks: {chunk_count}, Findings: {finding_count}")
        print(f"     EvidenceRefs: {ev_count}, Handovers: {handover_count}, Reviews: {review_count}, Audits: {audit_count}")
    finally:
        db.close()

def test_health_and_root_endpoints():
    """Verify health and root endpoints respond with 200 OK and expected structure."""
    print("\n[TEST 2] Testing Health and Root Endpoints...")
    health = health_check()
    assert health["status"] == "ok"
    assert health["database"] == "connected"
    print("  -> /health: OK -", health)

    rt = root()
    assert rt["team"] == "Web_hunter"
    assert rt["status"] == "HEALTHY"
    print("  -> /: OK -", rt)

def test_ten_logical_domain_routers():
    """Verify all 10 domain routers requested by Task 2 are operational."""
    print("\n[TEST 3] Testing 10 Logical Domain Modules...")
    db = SessionLocal()
    try:
        # 1. Auth Module
        login_res = login(UserLogin(email="admin@knowledgecontinuity.io", password="Password123!"), db=db)
        admin_user = login_res.user
        assert login_res.access_token is not None
        print("  -> 1. Auth Module: OK (Login successful, JWT token issued)")

        # 2. Users Module
        users = list_users(search=None, role=None, db=db, current_user=admin_user)
        assert len(users) >= 4
        print(f"  -> 2. Users Module: OK ({len(users)} users listed)")

        # 3. Projects Module
        projects = list_projects(db=db, current_user=admin_user)
        assert len(projects) > 0
        project_id = projects[0].id
        print(f"  -> 3. Projects Module: OK (Active project: {projects[0].name})")

        # 4. Documents Module
        docs = list_documents(project_id=project_id, db=db, current_user=admin_user)
        assert len(docs) >= 3
        print(f"  -> 4. Documents Module: OK ({len(docs)} source documents)")

        # 5. Extraction Module
        ext_status = get_extraction_status(current_user=admin_user)
        assert len(ext_status.supported_entity_types) == 10
        print(f"  -> 5. Extraction Module: OK (Supported entity types: {len(ext_status.supported_entity_types)})")

        # 6. Knowledge Module
        findings = list_findings(project_id=project_id, db=db, current_user=admin_user)
        assert len(findings) > 0
        print(f"  -> 6. Knowledge Module: OK ({len(findings)} findings retrieved)")

        # 7. Evidence Module
        finding_id = findings[0].id
        ev_refs = get_finding_evidence(finding_id=finding_id, db=db, current_user=admin_user)
        print(f"  -> 7. Evidence Module: OK ({len(ev_refs)} citations linked to finding)")

        # 8. Handovers Module
        handovers = list_handovers(project_id=project_id, db=db, current_user=admin_user)
        assert len(handovers) > 0
        print(f"  -> 8. Handovers Module: OK ({len(handovers)} handover reports)")

        # 9. Permissions Module
        matrix = get_permissions_matrix()
        assert "ADMIN" in matrix and "INCOMING_MEMBER" in matrix
        my_perms = get_my_permissions(current_user=admin_user)
        assert my_perms["role"] == "ADMIN"
        print("  -> 9. Permissions Module: OK (RBAC matrix configured)")

        # 10. Reviews Module
        queue = get_review_queue(project_id=project_id, db=db, current_user=admin_user)
        print(f"  -> 10. Reviews Module: OK (Review queue: {len(queue)} items)")

    finally:
        db.close()

def test_incoming_member_rbac_enforcement():
    """Verify backend enforces role-based restrictions for incoming members."""
    print("\n[TEST 4] Testing RBAC Security Enforcement for Incoming Member...")
    db = SessionLocal()
    try:
        incoming_user = db.query(User).filter(User.email == "incoming@knowledgecontinuity.io").first()
        project = db.query(Project).first()
        
        # Incoming member attempting to access manager review queue: must raise 403 HTTPException
        try:
            get_review_queue(project_id=project.id, db=db, current_user=incoming_user)
            assert False, "Should have raised 403 Forbidden"
        except HTTPException as e:
            assert e.status_code == 403
            print(f"  -> RBAC 403 Forbidden on Review Queue: ENFORCED ({e.detail})")
    finally:
        db.close()

if __name__ == "__main__":
    test_database_connection()
    test_health_and_root_endpoints()
    test_ten_logical_domain_routers()
    test_incoming_member_rbac_enforcement()
    print("\n=======================================================")
    print("ALL PHASE 1 FOUNDATION TESTS PASSED SUCCESSFULLY (100%)")
    print("=======================================================")
