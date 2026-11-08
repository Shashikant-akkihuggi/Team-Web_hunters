"""
Comprehensive Automated Test Suite for Phase 4:
AI Knowledge Extraction & Intelligence Engine

Tests:
1. Synthetic 3-document scenario:
   - Document 1: Architectural Decision (PostgreSQL) + Auth Task (Completed)
   - Document 2: Payment Integration (Rahul, deadline 2026-12-15) + DB migration dependency
   - Document 3: Payment Integration (Blocked pending gateway approval) + Legacy cache risk
2. Verification engine:
   - Quotation matching against chunk text (VERIFIED vs UNSUPPORTED)
   - Fabricated quotation detection
3. Contradiction detection engine:
   - Status conflict between Document 2 and Document 3 (Payment integration IN_PROGRESS vs BLOCKED)
   - Creation of KnowledgeConflict record
   - Preservation of both source quotations and page numbers
4. Extraction job lifecycle:
   - ExtractionJob created, metrics tracked, completed
5. Knowledge Hub APIs:
   - Decisions, tasks, risks, blockers, dependencies, questions, conflicts, evidence detail
"""

import sys
import os
import unittest
from datetime import datetime

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.app.database import SessionLocal, Base, engine
from backend.app.models import (
    User, UserRole, Project, ProjectStatus, Document, DocumentChunk,
    ExtractedFinding, EvidenceReference, ExtractionJob, ExtractionJobStatus,
    KnowledgeConflict, ConflictType, VerificationStatus
)
from backend.app.services.ai_service import AIService
from backend.app.services.verification_service import (
    calculate_match_score, run_project_verification
)
from backend.app.services.extraction_pipeline import run_extraction_pipeline
from backend.app.routers.knowledge import (
    get_project_knowledge_hub, get_project_decisions, get_project_tasks,
    get_project_conflicts, get_finding_evidence_detail
)
from backend.app.routers.extraction import (
    trigger_extraction, list_project_extractions, get_extraction_job
)


class TestPhase4AIEngine(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        Base.metadata.create_all(bind=engine)
        cls.db = SessionLocal()

        # Create test user
        cls.user = cls.db.query(User).filter(User.email == "phase4_ai_lead@webhunter.com").first()
        if not cls.user:
            cls.user = User(
                email="phase4_ai_lead@webhunter.com",
                hashed_password="hashed_password_placeholder",
                full_name="Phase 4 AI Test Lead",
                role=UserRole.ADMIN,
                is_active=True
            )
            cls.db.add(cls.user)
            cls.db.commit()
            cls.db.refresh(cls.user)

    @classmethod
    def tearDownClass(cls):
        cls.db.close()

    def setUp(self):
        # Create fresh test project
        self.project = Project(
            name=f"Phase 4 Acceptance Project {datetime.utcnow().timestamp()}",
            description="Testing AI extraction, verification, and contradiction detection",
            created_by=self.user.id,
            status=ProjectStatus.ACTIVE
        )
        self.db.add(self.project)
        self.db.commit()
        self.db.refresh(self.project)

    def tearDown(self):
        # Clean up project data
        if self.project:
            self.db.query(KnowledgeConflict).filter(KnowledgeConflict.project_id == self.project.id).delete()
            self.db.query(EvidenceReference).filter(
                EvidenceReference.finding_id.in_(
                    self.db.query(ExtractedFinding.id).filter(ExtractedFinding.project_id == self.project.id)
                )
            ).delete(synchronize_session=False)
            self.db.query(ExtractedFinding).filter(ExtractedFinding.project_id == self.project.id).delete()
            self.db.query(ExtractionJob).filter(ExtractionJob.project_id == self.project.id).delete()
            self.db.query(DocumentChunk).filter(DocumentChunk.project_id == self.project.id).delete()
            self.db.query(Document).filter(Document.project_id == self.project.id).delete()
            self.db.query(Project).filter(Project.id == self.project.id).delete()
            self.db.commit()

    def test_01_synthetic_three_document_extraction(self):
        """
        Verify that 3 documents with decisions, tasks, dependencies, and conflicts
        are ingested, chunked, and extracted accurately.
        """
        # Document 1: Architecture Note
        doc1 = Document(
            project_id=self.project.id,
            filename="arch_decision_note.txt",
            file_path="/uploads/arch_decision_note.txt",
            file_type="txt",
            file_hash="hash_doc1_arch",
            uploaded_by=self.user.id,
            status="PROCESSED",
            page_count=1
        )
        self.db.add(doc1)
        self.db.commit()
        self.db.refresh(doc1)

        chunk1 = DocumentChunk(
            project_id=self.project.id,
            document_id=doc1.id,
            page_number=1,
            chunk_index=0,
            text_content=(
                "Architecture Decision Record 01. "
                "We decided to use PostgreSQL for relational storage and pgvector for semantic retrieval. "
                "The core authentication service is completed and verified."
            )
        )
        self.db.add(chunk1)

        # Document 2: Sprint 4 Planning
        doc2 = Document(
            project_id=self.project.id,
            filename="sprint_4_plan.txt",
            file_path="/uploads/sprint_4_plan.txt",
            file_type="txt",
            file_hash="hash_doc2_plan",
            uploaded_by=self.user.id,
            status="PROCESSED",
            page_count=1
        )
        self.db.add(doc2)
        self.db.commit()
        self.db.refresh(doc2)

        chunk2 = DocumentChunk(
            project_id=self.project.id,
            document_id=doc2.id,
            page_number=1,
            chunk_index=0,
            text_content=(
                "Sprint Planning Notes. "
                "Payment integration is assigned to Rahul with deadline 2026-12-15. "
                "Database migration depends on PostgreSQL upgrade before running schema scripts."
            )
        )
        self.db.add(chunk2)

        # Document 3: Weekly Ops Update
        doc3 = Document(
            project_id=self.project.id,
            filename="weekly_ops_update.txt",
            file_path="/uploads/weekly_ops_update.txt",
            file_type="txt",
            file_hash="hash_doc3_ops",
            uploaded_by=self.user.id,
            status="PROCESSED",
            page_count=1
        )
        self.db.add(doc3)
        self.db.commit()
        self.db.refresh(doc3)

        chunk3 = DocumentChunk(
            project_id=self.project.id,
            document_id=doc3.id,
            page_number=1,
            chunk_index=0,
            text_content=(
                "Weekly Operations Incident & Status Update. "
                "Payment integration is blocked pending third-party gateway approval. "
                "There is a potential risk of single point of failure in our legacy cache layer."
            )
        )
        self.db.add(chunk3)
        self.db.commit()

        # Run Extraction Pipeline
        job = run_extraction_pipeline(
            project_id=self.project.id,
            user_id=self.user.id,
            db=self.db,
            force_reprocess=True
        )

        self.assertEqual(job.status, ExtractionJobStatus.COMPLETED)
        self.assertEqual(job.processed_documents_count, 3)
        self.assertEqual(job.processed_chunks_count, 3)
        self.assertGreater(job.extracted_findings_count, 0)

        # 1. Verify PostgreSQL decision
        decision = self.db.query(ExtractedFinding).filter(
            ExtractedFinding.project_id == self.project.id,
            ExtractedFinding.entity_type == "DECISION"
        ).first()
        self.assertIsNotNone(decision, "PostgreSQL decision must be extracted")
        self.assertIn("postgresql", decision.supporting_quotation.lower())
        self.assertEqual(decision.verification_status, VerificationStatus.VERIFIED)

        # 2. Verify Auth task completed
        auth_task = self.db.query(ExtractedFinding).filter(
            ExtractedFinding.project_id == self.project.id,
            ExtractedFinding.entity_type == "TASK",
            ExtractedFinding.supporting_quotation.ilike("%authentication service%")
        ).first()
        self.assertIsNotNone(auth_task, "Authentication task must be extracted")
        self.assertEqual(auth_task.task_status, "COMPLETED")
        self.assertEqual(auth_task.verification_status, VerificationStatus.VERIFIED)

        # 3. Verify Payment integration task assigned to Rahul
        payment_task = self.db.query(ExtractedFinding).filter(
            ExtractedFinding.project_id == self.project.id,
            ExtractedFinding.entity_type == "TASK",
            ExtractedFinding.supporting_quotation.ilike("%assigned to rahul%")
        ).first()
        self.assertIsNotNone(payment_task, "Payment integration task must be extracted")
        self.assertEqual(payment_task.owner, "Rahul")
        self.assertEqual(payment_task.deadline, "2026-12-15")

        # 4. Verify Database migration dependency
        dep = self.db.query(ExtractedFinding).filter(
            ExtractedFinding.project_id == self.project.id,
            ExtractedFinding.entity_type == "DEPENDENCY"
        ).first()
        self.assertIsNotNone(dep, "Database migration dependency must be extracted")
        self.assertIn("depends on postgresql upgrade", dep.supporting_quotation.lower())

        # 5. Verify Contradiction Detection for Payment integration
        conflicts = self.db.query(KnowledgeConflict).filter(
            KnowledgeConflict.project_id == self.project.id
        ).all()
        self.assertGreater(len(conflicts), 0, "A contradiction between IN_PROGRESS and BLOCKED must be detected")
        status_conflict = next((c for c in conflicts if c.conflict_type == ConflictType.STATUS), None)
        self.assertIsNotNone(status_conflict, "Status conflict record must exist")
        self.assertIn("payment integration", status_conflict.description.lower())

        # Confirm both sources are preserved with quotations
        self.assertIsNotNone(status_conflict.source_1_quote)
        self.assertIsNotNone(status_conflict.source_2_quote)

        # Confirm findings were flagged as CONFLICTED
        self.assertIn(payment_task.verification_status, [VerificationStatus.CONFLICTED, VerificationStatus.CONFLICTING])

    def test_02_unsupported_evidence_verification(self):
        """
        Verify that a finding with a fabricated quotation is marked UNSUPPORTED.
        """
        # Create a document and chunk
        doc = Document(
            project_id=self.project.id,
            filename="doc_unsupported_test.txt",
            file_path="/uploads/doc_unsupported_test.txt",
            file_type="txt",
            file_hash="hash_unsupported_1",
            uploaded_by=self.user.id,
            status="PROCESSED"
        )
        self.db.add(doc)
        self.db.commit()

        chunk = DocumentChunk(
            project_id=self.project.id,
            document_id=doc.id,
            page_number=1,
            chunk_index=0,
            text_content="This is the authentic document containing only verified facts about our server stack."
        )
        self.db.add(chunk)
        self.db.commit()

        # Add a finding with a completely fabricated quotation
        fake_finding = ExtractedFinding(
            project_id=self.project.id,
            document_id=doc.id,
            chunk_id=chunk.id,
            entity_type="TASK",
            title="Invented Secret Task",
            description="A task claiming something never stated in the text",
            supporting_quotation="We will migrate the entire cloud infra to Mars by next Friday.",
            page_number=1,
            status="DRAFT"
        )
        self.db.add(fake_finding)
        self.db.commit()

        # Run verification
        stats = run_project_verification(self.project.id, self.db)
        self.db.refresh(fake_finding)

        self.assertEqual(fake_finding.verification_status, VerificationStatus.UNSUPPORTED)
        self.assertTrue(fake_finding.flags.get("missing_evidence"))
        self.assertEqual(stats["unsupported_count"], 1)

    def test_03_knowledge_apis(self):
        """
        Test the knowledge hub and filterable endpoints directly.
        """
        # Create sample findings
        doc = Document(
            project_id=self.project.id,
            filename="api_test_doc.txt",
            file_path="/uploads/api_test_doc.txt",
            file_type="txt",
            file_hash="hash_api_doc",
            uploaded_by=self.user.id,
            status="PROCESSED"
        )
        self.db.add(doc)
        self.db.commit()

        chunk = DocumentChunk(
            project_id=self.project.id,
            document_id=doc.id,
            page_number=1,
            chunk_index=0,
            text_content="We decided to use Redis for session caching. The migration task is in progress."
        )
        self.db.add(chunk)
        self.db.commit()

        f1 = ExtractedFinding(
            project_id=self.project.id,
            document_id=doc.id,
            chunk_id=chunk.id,
            entity_type="DECISION",
            title="Decision: Redis Session Caching",
            description="Use Redis for session caching",
            supporting_quotation="We decided to use Redis for session caching.",
            page_number=1
        )
        f2 = ExtractedFinding(
            project_id=self.project.id,
            document_id=doc.id,
            chunk_id=chunk.id,
            entity_type="TASK",
            title="Migration Task",
            description="The migration task is in progress",
            task_status="IN_PROGRESS",
            supporting_quotation="The migration task is in progress.",
            page_number=1
        )
        self.db.add_all([f1, f2])
        self.db.commit()

        run_project_verification(self.project.id, self.db)

        # 1. Test Knowledge Hub endpoint
        hub = get_project_knowledge_hub(self.project.id, self.db, self.user)
        self.assertIn("summary", hub)
        self.assertIn("findings", hub)
        self.assertEqual(hub["summary"].total_findings, 2)
        self.assertEqual(hub["summary"].decisions_count, 1)
        self.assertEqual(hub["summary"].tasks_count, 1)

        # 2. Test Decisions endpoint
        decisions = get_project_decisions(self.project.id, None, self.db, self.user)
        self.assertEqual(len(decisions), 1)
        self.assertEqual(decisions[0].entity_type, "DECISION")

        # 3. Test Tasks endpoint
        tasks = get_project_tasks(self.project.id, None, None, None, None, self.db, self.user)
        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0].task_status, "IN_PROGRESS")

        # 4. Test Evidence detail endpoint
        evidence_detail = get_finding_evidence_detail(f1.id, self.db, self.user)
        self.assertEqual(evidence_detail.finding_id, f1.id)
        self.assertIsNotNone(evidence_detail.chunk_text)
        self.assertEqual(evidence_detail.document_filename, "api_test_doc.txt")
        self.assertTrue(evidence_detail.is_verified)

    def test_04_duplicate_suppression_and_rerun(self):
        """
        Verify that running extraction multiple times does not duplicate findings.
        """
        doc = Document(
            project_id=self.project.id,
            filename="dedup_doc.txt",
            file_path="/uploads/dedup_doc.txt",
            file_type="txt",
            file_hash="hash_dedup",
            uploaded_by=self.user.id,
            status="PROCESSED"
        )
        self.db.add(doc)
        self.db.commit()

        chunk = DocumentChunk(
            project_id=self.project.id,
            document_id=doc.id,
            page_number=1,
            chunk_index=0,
            text_content="We decided to use Docker Compose for local development testing."
        )
        self.db.add(chunk)
        self.db.commit()

        # Run extraction 1st time
        job1 = run_extraction_pipeline(self.project.id, self.user.id, self.db, force_reprocess=True)
        count1 = self.db.query(ExtractedFinding).filter(ExtractedFinding.project_id == self.project.id).count()

        # Run extraction 2nd time
        job2 = run_extraction_pipeline(self.project.id, self.user.id, self.db, force_reprocess=True)
        count2 = self.db.query(ExtractedFinding).filter(ExtractedFinding.project_id == self.project.id).count()

        self.assertEqual(count1, count2, "Rerunning extraction pipeline must replace DRAFT findings, not duplicate them")

    def test_05_deadline_and_ownership_conflicts(self):
        """
        Verify detection of contradictory deadlines and conflicting assigned owners.
        """
        doc1 = Document(
            project_id=self.project.id,
            filename="roadmap_v1.txt",
            file_path="/uploads/roadmap_v1.txt",
            file_type="txt",
            file_hash="hash_rm1",
            uploaded_by=self.user.id,
            status="PROCESSED"
        )
        doc2 = Document(
            project_id=self.project.id,
            filename="roadmap_v2.txt",
            file_path="/uploads/roadmap_v2.txt",
            file_type="txt",
            file_hash="hash_rm2",
            uploaded_by=self.user.id,
            status="PROCESSED"
        )
        self.db.add_all([doc1, doc2])
        self.db.commit()

        chunk1 = DocumentChunk(
            project_id=self.project.id,
            document_id=doc1.id,
            page_number=1,
            chunk_index=0,
            text_content="Mobile App release is assigned to Priya with deadline 2026-10-01."
        )
        chunk2 = DocumentChunk(
            project_id=self.project.id,
            document_id=doc2.id,
            page_number=2,
            chunk_index=0,
            text_content="Mobile App release is assigned to Amit with deadline 2027-02-15."
        )
        self.db.add_all([chunk1, chunk2])
        self.db.commit()

        job = run_extraction_pipeline(self.project.id, self.user.id, self.db, force_reprocess=True)
        self.assertEqual(job.status, ExtractionJobStatus.COMPLETED)

        conflicts = self.db.query(KnowledgeConflict).filter(KnowledgeConflict.project_id == self.project.id).all()
        self.assertGreaterEqual(len(conflicts), 1, "Conflict must be detected between conflicting roadmaps")
        conflict = conflicts[0]
        self.assertIn(conflict.conflict_type, [ConflictType.OWNERSHIP, ConflictType.DEADLINE, ConflictType.STATUS])
        self.assertIsNotNone(conflict.source_1_quote)
        self.assertIsNotNone(conflict.source_2_quote)


if __name__ == "__main__":
    unittest.main()
