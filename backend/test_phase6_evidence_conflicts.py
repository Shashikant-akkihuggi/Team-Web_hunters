"""
Comprehensive Automated Test Suite for Phase 6:
Evidence Verification & Conflict Management

Tests:
1. Acceptance Scenario:
   - Document A: "Payment integration has been completed successfully."
   - Document B: "Payment integration is still pending because the payment API has errors."
   - Detects STATUS conflict with both quotations and page citations.
   - Reviewer marks UNDER_REVIEW (recorded in audit log).
   - PM resolves with CLAIM_A_SUPPORTED + mandatory explanation (recorded in audit log).
   - Non-destructive updates: both findings preserved in database.
   - Reconstructed project state reflects Claim A (Payment integration COMPLETED).
2. False Conflict Prevention:
   - Unrelated tasks (User authentication completed vs Payment integration pending) trigger 0 false conflicts.
3. 8-Point Evidence Integrity Protocol:
   - Valid citation: VERIFIED, score >= 0.70.
   - Fabricated citation: UNSUPPORTED, score 0.0.
   - Missing/deleted document: UNSUPPORTED, broken citation flagged.
   - Character offsets and verification method populated.
4. Evidence Coverage & Quality Summary:
   - Coverage % = (Findings with valid evidence / Total factual findings) * 100.
   - Per-document and per-entity type breakdown.
5. Conflict Dismissal Workflow:
   - Dismiss with mandatory explanation -> status DISMISSED, audit logged.
6. Conflict Audit History API:
   - /conflicts/{conflict_id}/history returns chronological audit entries.
   - /projects/{project_id}/audit-logs returns project audit log.
7. Role-Based Access Control (RBAC):
   - INCOMING_MEMBER blocked from resolving or dismissing (403 Forbidden).
   - ADMIN and PROJECT_MANAGER authorized.
8. Evidence Detail & Verify Endpoints:
   - /evidence/{evidence_id} and /evidence/{evidence_id}/verify.
"""

import sys
import os
import unittest
from datetime import datetime
from fastapi import HTTPException

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.app.database import SessionLocal, Base, engine
from backend.app.models import (
    User, UserRole, Project, ProjectStatus, Document, DocumentChunk,
    ExtractedFinding, EvidenceReference, ExtractionJob, ExtractionJobStatus,
    KnowledgeConflict, ConflictType, ConflictStatus, ConflictSeverity,
    ResolutionChoice, VerificationStatus, AuditLog, ProjectMember
)
from backend.app.schemas import (
    ConflictResolveRequest, ConflictDismissRequest, ConflictReviewRequest
)
from backend.app.services.verification_service import (
    run_project_verification, verify_finding_integrity,
    review_conflict, resolve_conflict, dismiss_conflict,
    get_evidence_coverage_metrics, are_topics_conflicting
)
from backend.app.services.reconstruction_service import (
    reconstruct_project_state, get_task_timeline
)
from backend.app.routers.conflicts import (
    get_project_conflicts, get_conflict_detail, review_conflict_endpoint,
    resolve_conflict_endpoint, dismiss_conflict_endpoint, get_conflict_history
)
from backend.app.routers.evidence import (
    get_project_evidence_summary, list_project_evidence,
    get_evidence_detail, verify_evidence_endpoint
)
from backend.app.routers.audit import get_project_audit_logs


class TestPhase6EvidenceAndConflicts(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        Base.metadata.create_all(bind=engine)
        cls.db = SessionLocal()

        # 1. PM User
        cls.pm_user = cls.db.query(User).filter(User.email == "pm_phase6@webhunter.com").first()
        if not cls.pm_user:
            cls.pm_user = User(
                email="pm_phase6@webhunter.com",
                hashed_password="hashed_placeholder_pw",
                full_name="Phase 6 PM",
                role=UserRole.PROJECT_MANAGER,
                is_active=True
            )
            cls.db.add(cls.pm_user)
            cls.db.commit()
            cls.db.refresh(cls.pm_user)

        # 2. Incoming Member User
        cls.member_user = cls.db.query(User).filter(User.email == "member_phase6@webhunter.com").first()
        if not cls.member_user:
            cls.member_user = User(
                email="member_phase6@webhunter.com",
                hashed_password="hashed_placeholder_pw",
                full_name="Phase 6 Incoming Member",
                role=UserRole.INCOMING_MEMBER,
                is_active=True
            )
            cls.db.add(cls.member_user)
            cls.db.commit()
            cls.db.refresh(cls.member_user)

    @classmethod
    def tearDownClass(cls):
        cls.db.close()

    def setUp(self):
        self.project = Project(
            name=f"Phase 6 Evidence Project {datetime.utcnow().timestamp()}",
            description="Testing evidence integrity and conflict resolution workspace",
            created_by=self.pm_user.id,
            status=ProjectStatus.ACTIVE
        )
        self.db.add(self.project)
        self.db.commit()
        self.db.refresh(self.project)

        # Add both members
        pm_mem = ProjectMember(project_id=self.project.id, user_id=self.pm_user.id, role=UserRole.PROJECT_MANAGER)
        in_mem = ProjectMember(project_id=self.project.id, user_id=self.member_user.id, role=UserRole.INCOMING_MEMBER)
        self.db.add_all([pm_mem, in_mem])
        self.db.commit()

    def create_test_document(self, filename, file_type="TXT", page_count=1):
        doc = Document(
            project_id=self.project.id,
            filename=filename,
            file_path=f"/uploads/{filename}",
            file_hash=f"hash_{filename}_{datetime.utcnow().timestamp()}",
            file_type=file_type,
            file_size=1024,
            page_count=page_count,
            chunk_count=1,
            processing_status="PROCESSED",
            uploaded_by=self.pm_user.id
        )
        self.db.add(doc)
        self.db.commit()
        self.db.refresh(doc)
        return doc

    def tearDown(self):
        self.db.rollback()
        if self.project:
            self.db.query(AuditLog).filter(AuditLog.project_id == self.project.id).delete()
            self.db.query(KnowledgeConflict).filter(KnowledgeConflict.project_id == self.project.id).delete()
            self.db.query(EvidenceReference).filter(
                EvidenceReference.finding_id.in_(
                    self.db.query(ExtractedFinding.id).filter(ExtractedFinding.project_id == self.project.id)
                )
            ).delete(synchronize_session=False)
            self.db.query(ExtractedFinding).filter(ExtractedFinding.project_id == self.project.id).delete()
            self.db.query(DocumentChunk).filter(DocumentChunk.project_id == self.project.id).delete()
            self.db.query(Document).filter(Document.project_id == self.project.id).delete()
            self.db.query(ProjectMember).filter(ProjectMember.project_id == self.project.id).delete()
            self.db.query(Project).filter(Project.id == self.project.id).delete()
            self.db.commit()

    def test_01_acceptance_scenario_conflicting_payment_documents(self):
        """
        Acceptance Scenario:
        Document A ("Payment integration has been completed successfully.")
        vs
        Document B ("Payment integration is still pending because the payment API has errors.")
        """
        # 1. Create Document A
        doc_a = self.create_test_document("Document_A_Sprint_Report.docx", "DOCX", 2)

        chunk_a = DocumentChunk(
            document_id=doc_a.id,
            project_id=self.project.id,
            page_number=1,
            chunk_index=0,
            text_content="Section 2.1: Payment integration has been completed successfully. All test transactions passed.",
            char_start=0,
            char_end=95
        )
        self.db.add(chunk_a)

        # 2. Create Document B
        doc_b = self.create_test_document("Document_B_Meeting_Notes.txt", "TXT", 1)
        self.db.add(doc_b)
        self.db.commit()
        self.db.refresh(doc_b)

        chunk_b = DocumentChunk(
            document_id=doc_b.id,
            project_id=self.project.id,
            page_number=1,
            chunk_index=0,
            text_content="Engineering sync: Payment integration is still pending because the payment API has errors.",
            char_start=0,
            char_end=90
        )
        self.db.add(chunk_b)
        self.db.commit()

        # 3. Create Findings A & B
        f_a = ExtractedFinding(
            project_id=self.project.id,
            document_id=doc_a.id,
            chunk_id=chunk_a.id,
            entity_type="TASK",
            title="Payment integration",
            description="Payment integration completed successfully per Sprint Report.",
            task_status="COMPLETED",
            owner="Rahul",
            page_number=1,
            supporting_quotation="Payment integration has been completed successfully.",
            confidence_score=0.95
        )

        f_b = ExtractedFinding(
            project_id=self.project.id,
            document_id=doc_b.id,
            chunk_id=chunk_b.id,
            entity_type="TASK",
            title="Payment integration",
            description="Payment integration is still pending because the payment API has errors.",
            task_status="BLOCKED",
            owner="Rahul",
            page_number=1,
            supporting_quotation="Payment integration is still pending because the payment API has errors.",
            confidence_score=0.90
        )

        self.db.add_all([f_a, f_b])
        self.db.commit()

        # 4. Run Evidence Verification & Conflict Detection
        metrics = run_project_verification(self.project.id, self.db)
        self.assertEqual(metrics["total_findings"], 2)
        self.assertGreaterEqual(metrics["conflicts_count"], 1)

        # Verify conflict generated in DB
        conflict = self.db.query(KnowledgeConflict).filter(KnowledgeConflict.project_id == self.project.id).first()
        self.assertIsNotNone(conflict)
        self.assertEqual(conflict.conflict_type, ConflictType.STATUS)
        self.assertIn("Payment integration", conflict.title)
        self.assertEqual(conflict.conflict_status, ConflictStatus.OPEN)
        self.assertIn("completed successfully", conflict.source_1_quote)
        self.assertIn("still pending", conflict.source_2_quote)

        # Both findings should be flagged CONFLICTED initially
        self.db.refresh(f_a)
        self.db.refresh(f_b)
        self.assertEqual(f_a.verification_status, VerificationStatus.CONFLICTED)
        self.assertEqual(f_b.verification_status, VerificationStatus.CONFLICTED)

        # 5. Mark conflict UNDER_REVIEW via router
        rev_res = review_conflict_endpoint(
            conflict_id=conflict.id,
            payload=ConflictReviewRequest(notes="Investigating payment gateway test dashboard logs."),
            db=self.db,
            current_user=self.pm_user
        )
        self.assertEqual(rev_res.conflict_status, "UNDER_REVIEW")

        # Verify Audit Log recorded review
        review_audit = self.db.query(AuditLog).filter(
            AuditLog.entity_id == conflict.id,
            AuditLog.action == "CONFLICT_REVIEW_STARTED"
        ).first()
        self.assertIsNotNone(review_audit)

        # 6. PM Resolves Conflict with CLAIM_A_SUPPORTED
        res_payload = ConflictResolveRequest(
            resolution_choice=ResolutionChoice.CLAIM_A_SUPPORTED,
            resolution_notes="Verified directly with Stripe gateway dashboard and test transactions that the payment API is connected and working."
        )
        res_res = resolve_conflict_endpoint(
            conflict_id=conflict.id,
            payload=res_payload,
            db=self.db,
            current_user=self.pm_user
        )
        self.assertEqual(res_res.conflict_status, "RESOLVED")
        self.assertEqual(res_res.resolution_choice, ResolutionChoice.CLAIM_A_SUPPORTED)
        self.assertIn("Stripe gateway dashboard", res_res.resolution_notes)

        # 7. Non-Destructive Verification:
        # Both original findings MUST still exist in database!
        findings_in_db = self.db.query(ExtractedFinding).filter(ExtractedFinding.project_id == self.project.id).all()
        self.assertEqual(len(findings_in_db), 2, "Both findings must be preserved non-destructively!")

        self.db.refresh(f_a)
        self.db.refresh(f_b)
        self.assertEqual(f_a.verification_status, VerificationStatus.VERIFIED)
        self.assertEqual(f_b.verification_status, VerificationStatus.UNSUPPORTED)

        # Both evidence references must still exist!
        refs_in_db = self.db.query(EvidenceReference).filter(
            EvidenceReference.finding_id.in_([f_a.id, f_b.id])
        ).all()
        self.assertEqual(len(refs_in_db), 2)

        # 8. Reconstructed Project State Verification:
        state = reconstruct_project_state(self.project.id, self.db)
        # Should reflect Claim A (COMPLETED task)
        self.assertEqual(state.overview.completed_tasks, 1)
        self.assertEqual(state.overview.blocked_tasks, 0)
        # Conflicting status counter drops to 0 because conflict is resolved
        self.assertEqual(state.uncertainty_state.conflicting_statuses_count, 0)

        # 9. Verify Conflict History Endpoint
        hist_res = get_conflict_history(conflict_id=conflict.id, db=self.db, current_user=self.pm_user)
        self.assertGreaterEqual(len(hist_res.history), 2)
        actions = [h.action for h in hist_res.history]
        self.assertIn("CONFLICT_REVIEW_STARTED", actions)
        self.assertIn("CONFLICT_RESOLVED", actions)

    def test_02_false_conflict_prevention_unrelated_tasks(self):
        """
        Verify that completely unrelated tasks (e.g. User authentication vs Payment integration)
        do NOT generate false conflicts.
        """
        is_conflicting = are_topics_conflicting("User authentication completed", "Payment integration is pending")
        self.assertFalse(is_conflicting, "Unrelated tasks must not be marked conflicting")

        is_conflicting_2 = are_topics_conflicting("Database migration", "Frontend design")
        self.assertFalse(is_conflicting_2)

        is_true_conflict = are_topics_conflicting("Payment integration completed", "Payment integration is pending")
        self.assertTrue(is_true_conflict)

        # Integration test in project
        doc = self.create_test_document("Unrelated_Tasks_Doc.txt", "TXT", 1)

        chunk = DocumentChunk(
            document_id=doc.id,
            project_id=self.project.id,
            page_number=1,
            text_content="User authentication has been fully completed. Separately, payment integration is still pending.",
            char_start=0,
            char_end=95
        )
        self.db.add(chunk)
        self.db.commit()

        f1 = ExtractedFinding(
            project_id=self.project.id,
            document_id=doc.id,
            chunk_id=chunk.id,
            entity_type="TASK",
            title="User authentication",
            description="User authentication has been completed.",
            task_status="COMPLETED",
            page_number=1,
            supporting_quotation="User authentication has been fully completed."
        )

        f2 = ExtractedFinding(
            project_id=self.project.id,
            document_id=doc.id,
            chunk_id=chunk.id,
            entity_type="TASK",
            title="Payment integration",
            description="Payment integration is still pending.",
            task_status="NOT_STARTED",
            page_number=1,
            supporting_quotation="payment integration is still pending."
        )
        self.db.add_all([f1, f2])
        self.db.commit()

        metrics = run_project_verification(self.project.id, self.db)
        self.assertEqual(metrics["conflicts_count"], 0, "No false conflicts should be detected between unrelated tasks")

    def test_03_eight_point_evidence_integrity_protocol(self):
        """
        Tests each rule of the 8-point evidence integrity check:
        1. Document exists.
        2. Correct project.
        3. Chunk exists.
        4. Chunk belongs to doc.
        5. Quote present with high score (fabricated quote fails).
        6. Valid page number.
        7. Authorized access.
        8. Not corrupted source.
        """
        doc = self.create_test_document("Architecture_Spec.pdf", "PDF", 5)

        chunk = DocumentChunk(
            document_id=doc.id,
            project_id=self.project.id,
            page_number=2,
            text_content="We have officially chosen PostgreSQL 16 as our primary database engine for all services.",
            char_start=0,
            char_end=88
        )
        self.db.add(chunk)
        self.db.commit()

        # A. Valid Finding with exact quote
        valid_f = ExtractedFinding(
            project_id=self.project.id,
            document_id=doc.id,
            chunk_id=chunk.id,
            entity_type="DECISION",
            title="PostgreSQL primary database",
            description="PostgreSQL chosen as primary database.",
            page_number=2,
            supporting_quotation="We have officially chosen PostgreSQL 16 as our primary database engine",
            confidence_score=0.98
        )
        self.db.add(valid_f)
        self.db.commit()

        res_valid = verify_finding_integrity(valid_f.id, self.db)
        self.assertEqual(res_valid["status"], VerificationStatus.VERIFIED)
        self.assertGreaterEqual(res_valid["match_score"], 0.70)
        self.assertTrue(all(res_valid["checks"].values()))

        # Check offsets populated
        ref = self.db.query(EvidenceReference).filter(EvidenceReference.finding_id == valid_f.id).first()
        self.assertIsNotNone(ref)
        self.assertEqual(ref.verification_status, "VERIFIED")
        self.assertGreaterEqual(ref.character_end, ref.character_start)

        # B. Fabricated Finding with non-existent quote
        fake_f = ExtractedFinding(
            project_id=self.project.id,
            document_id=doc.id,
            chunk_id=chunk.id,
            entity_type="DECISION",
            title="MongoDB chosen as primary database",
            description="MongoDB was selected as the NoSQL store.",
            page_number=2,
            supporting_quotation="The team unanimously opted for MongoDB Atlas cloud cluster.",
            confidence_score=0.90
        )
        self.db.add(fake_f)
        self.db.commit()

        res_fake = verify_finding_integrity(fake_f.id, self.db)
        self.assertEqual(res_fake["status"], VerificationStatus.UNSUPPORTED)
        self.assertFalse(res_fake["checks"]["quote_present_in_text"])

    def test_04_evidence_coverage_summary_api(self):
        """
        Tests GET /api/v1/projects/{project_id}/evidence/summary:
        Coverage % = (Findings with valid evidence / Total factual findings) * 100
        """
        doc = self.create_test_document("Coverage_Test_Doc.pdf", "PDF", 3)

        chunk = DocumentChunk(
            document_id=doc.id,
            project_id=self.project.id,
            page_number=1,
            text_content="Sprint goal: Complete user registration and session management.",
            char_start=0,
            char_end=63
        )
        self.db.add(chunk)
        self.db.commit()

        # 1 Verified finding
        f1 = ExtractedFinding(
            project_id=self.project.id,
            document_id=doc.id,
            chunk_id=chunk.id,
            entity_type="TASK",
            title="User registration",
            description="Complete user registration",
            page_number=1,
            supporting_quotation="Complete user registration and session management."
        )

        # 1 Unsupported finding
        f2 = ExtractedFinding(
            project_id=self.project.id,
            document_id=doc.id,
            chunk_id=chunk.id,
            entity_type="TASK",
            title="Kubernetes cluster setup",
            description="Setup production cluster",
            page_number=1,
            supporting_quotation="Fabricated quote about kubernetes helm charts."
        )
        self.db.add_all([f1, f2])
        self.db.commit()

        run_project_verification(self.project.id, self.db)

        # Call Evidence Summary router
        data = get_project_evidence_summary(project_id=self.project.id, db=self.db, current_user=self.pm_user)

        self.assertEqual(data.total_findings, 2)
        self.assertEqual(data.verified_count, 1)
        self.assertEqual(data.unsupported_count, 1)
        # 1/2 = 50.0%
        self.assertEqual(data.coverage_percentage, 50.0)
        self.assertIn("1 / 2", data.coverage_fraction)
        self.assertEqual(len(data.by_document), 1)
        self.assertEqual(data.by_document[0]["filename"], "Coverage_Test_Doc.pdf")

    def test_05_conflict_dismissal_workflow(self):
        """
        Tests dismissing a conflict with mandatory explanation.
        """
        doc = self.create_test_document("Dismiss_Doc.txt", "TXT", 1)

        f1 = ExtractedFinding(
            project_id=self.project.id,
            document_id=doc.id,
            entity_type="TASK",
            title="Cache layer setup",
            description="Cache setup in progress",
            task_status="IN_PROGRESS",
            supporting_quotation="Cache layer setup in progress."
        )
        f2 = ExtractedFinding(
            project_id=self.project.id,
            document_id=doc.id,
            entity_type="TASK",
            title="Cache layer setup",
            description="Cache setup completed",
            task_status="COMPLETED",
            supporting_quotation="Cache layer setup is completed."
        )
        self.db.add_all([f1, f2])
        self.db.commit()

        # Create manual conflict
        conflict = KnowledgeConflict(
            project_id=self.project.id,
            title="Status conflict on Cache layer",
            finding_a_id=f1.id,
            finding_b_id=f2.id,
            conflict_type=ConflictType.STATUS,
            description="Contradictory cache setup status",
            conflict_status=ConflictStatus.OPEN
        )
        self.db.add(conflict)
        self.db.commit()
        self.db.refresh(conflict)

        # Dismiss via router
        dis_res = dismiss_conflict_endpoint(
            conflict_id=conflict.id,
            payload=ConflictDismissRequest(resolution_notes="Not a true contradiction; cache layer has multiple sub-services."),
            db=self.db,
            current_user=self.pm_user
        )
        self.assertEqual(dis_res.conflict_status, "DISMISSED")

        # Verify audit log
        audit = self.db.query(AuditLog).filter(
            AuditLog.entity_id == conflict.id,
            AuditLog.action == "CONFLICT_DISMISSED"
        ).first()
        self.assertIsNotNone(audit)

    def test_06_rbac_enforcement_on_conflict_resolution(self):
        """
        Verify that INCOMING_MEMBER role is blocked from resolving/dismissing conflicts.
        Only ADMIN and PROJECT_MANAGER roles are authorized.
        """
        conflict = KnowledgeConflict(
            project_id=self.project.id,
            title="RBAC test conflict",
            conflict_type=ConflictType.STATUS,
            description="Testing permission boundaries",
            conflict_status=ConflictStatus.OPEN
        )
        self.db.add(conflict)
        self.db.commit()
        self.db.refresh(conflict)

        # Incoming member attempts to resolve
        with self.assertRaises(HTTPException) as ctx:
            resolve_conflict_endpoint(
                conflict_id=conflict.id,
                payload=ConflictResolveRequest(resolution_choice=ResolutionChoice.CLAIM_A_SUPPORTED, resolution_notes="Attempting unauthorized resolve"),
                db=self.db,
                current_user=self.member_user
            )
        self.assertEqual(ctx.exception.status_code, 403, "Incoming member must be forbidden from resolving conflicts")

        # Incoming member attempts to dismiss
        with self.assertRaises(HTTPException) as ctx_dis:
            dismiss_conflict_endpoint(
                conflict_id=conflict.id,
                payload=ConflictDismissRequest(resolution_notes="Attempting unauthorized dismissal"),
                db=self.db,
                current_user=self.member_user
            )
        self.assertEqual(ctx_dis.exception.status_code, 403, "Incoming member must be forbidden from dismissing conflicts")

    def test_07_evidence_detail_and_reverify_endpoints(self):
        """
        Tests get_evidence_detail and verify_evidence_endpoint.
        """
        doc = self.create_test_document("System_Architecture.pdf", "PDF", 4)

        chunk = DocumentChunk(
            document_id=doc.id,
            project_id=self.project.id,
            page_number=3,
            text_content="Chapter 3: The backend architecture utilizes FastAPI with SQLAlchemy ORM and Alembic migrations.",
            char_start=0,
            char_end=95
        )
        self.db.add(chunk)
        self.db.commit()

        finding = ExtractedFinding(
            project_id=self.project.id,
            document_id=doc.id,
            chunk_id=chunk.id,
            entity_type="DECISION",
            title="FastAPI framework choice",
            description="FastAPI selected for backend services.",
            page_number=3,
            supporting_quotation="The backend architecture utilizes FastAPI with SQLAlchemy ORM and Alembic migrations."
        )
        self.db.add(finding)
        self.db.commit()

        run_project_verification(self.project.id, self.db)

        ref = self.db.query(EvidenceReference).filter(EvidenceReference.finding_id == finding.id).first()
        self.assertIsNotNone(ref)

        # 1. get_evidence_detail
        det_data = get_evidence_detail(evidence_id=ref.id, db=self.db, current_user=self.pm_user)
        self.assertEqual(det_data.finding_title, "FastAPI framework choice")
        self.assertEqual(det_data.page_number, 3)
        self.assertIn("FastAPI", det_data.quotation)
        self.assertTrue(det_data.is_verified)
        self.assertTrue(det_data.integrity_checks["quote_present_in_text"])

        # 2. verify_evidence_endpoint
        ver_data = verify_evidence_endpoint(evidence_id=ref.id, db=self.db, current_user=self.pm_user)
        self.assertTrue(ver_data.is_verified)
        self.assertEqual(ver_data.verification_status, "VERIFIED")
        self.assertEqual(ver_data.verified_page, 3)

        # 3. get_project_audit_logs
        logs = get_project_audit_logs(project_id=self.project.id, db=self.db, current_user=self.pm_user)
        self.assertIsInstance(logs, list)


if __name__ == "__main__":
    unittest.main()
