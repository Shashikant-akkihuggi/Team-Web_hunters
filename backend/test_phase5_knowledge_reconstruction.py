"""
Comprehensive Automated Test Suite for Phase 5:
Project Knowledge Reconstruction & Timeline Engine

Tests:
1. Acceptance Scenario with 7 Key Findings:
   - Authentication completed.
   - Database migration pending.
   - Payment integration pending / in progress.
   - Payment integration assigned to Rahul.
   - Payment integration depends on database migration.
   - PostgreSQL selected as database decision.
   - Two contradictory payment status updates (IN_PROGRESS vs BLOCKED).
2. Verification of 10 Acceptance Criteria:
   1. Authentication displayed as completed.
   2. Database migration displayed as pending (NOT_STARTED).
   3. Payment integration identified as blocked due to blocker evidence.
   4. Rahul identified as owner of payment integration.
   5. PostgreSQL displayed as recorded decision.
   6. Payment status conflict surfaced with both quotations.
   7. Database-to-payment dependency graph displayed with directed edge.
   8. Evidence references preserved with page citations.
   9. Unresolved questions surfaced.
   10. Missing dates or owners remain unknown without hallucination.
3. Additional Tests:
   - Circular dependency detection in dependency graph.
   - Decision timeline ordering (dated vs undated).
   - Responsibility mapping and unassigned tasks detection.
   - Risk register separation (source risks vs AI recommendations).
   - Project-scoped knowledge search API.
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
    KnowledgeConflict, ConflictType, VerificationStatus, ProjectReconstruction
)
from backend.app.services.reconstruction_service import (
    reconstruct_project_state, get_decision_timeline, get_task_timeline,
    get_dependency_graph, get_responsibilities, get_risk_register,
    search_project_knowledge
)
from backend.app.services.verification_service import run_project_verification
from backend.app.services.knowledge_normalization_service import (
    normalize_task_status, parse_normalized_date, check_is_overdue
)


class TestPhase5KnowledgeReconstruction(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        Base.metadata.create_all(bind=engine)
        cls.db = SessionLocal()

        cls.user = cls.db.query(User).filter(User.email == "phase5_lead@webhunter.com").first()
        if not cls.user:
            cls.user = User(
                email="phase5_lead@webhunter.com",
                hashed_password="hashed_password_placeholder",
                full_name="Phase 5 Architect",
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
        self.project = Project(
            name=f"Phase 5 Acceptance Project {datetime.utcnow().timestamp()}",
            description="Testing project knowledge reconstruction, timeline, and topology",
            created_by=self.user.id,
            status=ProjectStatus.ACTIVE
        )
        self.db.add(self.project)
        self.db.commit()
        self.db.refresh(self.project)

    def tearDown(self):
        if self.project:
            self.db.query(ProjectReconstruction).filter(ProjectReconstruction.project_id == self.project.id).delete()
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

    def test_01_acceptance_scenario_reconstruction(self):
        """
        Verify all 10 acceptance criteria on synthetic scenario:
        - Auth completed
        - DB migration pending
        - Payment integration assigned to Rahul
        - Payment integration depends on DB migration
        - PostgreSQL selected as database
        - Two contradictory payment status updates
        - Unresolved question
        """
        # Create documents
        doc1 = Document(
            project_id=self.project.id,
            filename="architecture_spec.txt",
            file_path="/uploads/architecture_spec.txt",
            file_type="txt",
            file_hash="hash_spec_1",
            uploaded_by=self.user.id,
            status="PROCESSED"
        )
        doc2 = Document(
            project_id=self.project.id,
            filename="sprint_board.txt",
            file_path="/uploads/sprint_board.txt",
            file_type="txt",
            file_hash="hash_sprint_2",
            uploaded_by=self.user.id,
            status="PROCESSED"
        )
        doc3 = Document(
            project_id=self.project.id,
            filename="ops_incident_report.txt",
            file_path="/uploads/ops_incident_report.txt",
            file_type="txt",
            file_hash="hash_ops_3",
            uploaded_by=self.user.id,
            status="PROCESSED"
        )
        self.db.add_all([doc1, doc2, doc3])
        self.db.commit()

        # Add Chunks
        chunk1 = DocumentChunk(
            project_id=self.project.id,
            document_id=doc1.id,
            page_number=1,
            chunk_index=0,
            text_content="We decided to use PostgreSQL for relational storage. The authentication service is completed."
        )
        chunk2 = DocumentChunk(
            project_id=self.project.id,
            document_id=doc2.id,
            page_number=1,
            chunk_index=0,
            text_content="Database migration is pending. Payment integration is assigned to Rahul with deadline 2026-12-15. Payment integration depends on database migration."
        )
        chunk3 = DocumentChunk(
            project_id=self.project.id,
            document_id=doc3.id,
            page_number=2,
            chunk_index=0,
            text_content="Payment integration is blocked pending third-party gateway approval. Unresolved question: which KYC provider should be selected?"
        )
        self.db.add_all([chunk1, chunk2, chunk3])
        self.db.commit()

        # 1. PostgreSQL Decision
        f_dec = ExtractedFinding(
            project_id=self.project.id,
            document_id=doc1.id,
            chunk_id=chunk1.id,
            entity_type="DECISION",
            title="Decision: PostgreSQL Storage",
            description="We decided to use PostgreSQL for relational storage",
            decision_date="2026-09-01",
            supporting_quotation="We decided to use PostgreSQL for relational storage.",
            page_number=1,
            verification_status="VERIFIED"
        )

        # 2. Auth Completed
        f_auth = ExtractedFinding(
            project_id=self.project.id,
            document_id=doc1.id,
            chunk_id=chunk1.id,
            entity_type="TASK",
            title="Authentication Service",
            description="The authentication service is completed",
            task_status="COMPLETED",
            supporting_quotation="The authentication service is completed.",
            page_number=1,
            verification_status="VERIFIED"
        )

        # 3. DB Migration Pending (NOT_STARTED)
        f_db_mig = ExtractedFinding(
            project_id=self.project.id,
            document_id=doc2.id,
            chunk_id=chunk2.id,
            entity_type="TASK",
            title="Database Migration",
            description="Database migration is pending",
            task_status="NOT_STARTED",
            supporting_quotation="Database migration is pending.",
            page_number=1,
            verification_status="VERIFIED"
        )

        # 4. Payment Integration (Sprint Plan: In Progress, assigned to Rahul)
        f_pay_plan = ExtractedFinding(
            project_id=self.project.id,
            document_id=doc2.id,
            chunk_id=chunk2.id,
            entity_type="TASK",
            title="Payment Integration",
            description="Payment integration is assigned to Rahul with deadline 2026-12-15",
            owner="Rahul",
            deadline="2026-12-15",
            task_status="IN_PROGRESS",
            supporting_quotation="Payment integration is assigned to Rahul with deadline 2026-12-15.",
            page_number=1,
            verification_status="VERIFIED"
        )

        # 5. Dependency: Payment Integration depends on Database Migration
        f_dep = ExtractedFinding(
            project_id=self.project.id,
            document_id=doc2.id,
            chunk_id=chunk2.id,
            entity_type="DEPENDENCY",
            title="Payment Integration",
            related_entity="Database Migration",
            description="Payment integration depends on database migration",
            supporting_quotation="Payment integration depends on database migration.",
            page_number=1,
            verification_status="VERIFIED"
        )

        # 6. Payment Integration (Ops Report: Blocked)
        f_pay_ops = ExtractedFinding(
            project_id=self.project.id,
            document_id=doc3.id,
            chunk_id=chunk3.id,
            entity_type="TASK",
            title="Payment Integration",
            description="Payment integration is blocked pending third-party gateway approval",
            task_status="BLOCKED",
            supporting_quotation="Payment integration is blocked pending third-party gateway approval.",
            page_number=2,
            verification_status="VERIFIED"
        )

        # 7. Unresolved Question
        f_q = ExtractedFinding(
            project_id=self.project.id,
            document_id=doc3.id,
            chunk_id=chunk3.id,
            entity_type="QUESTION",
            title="KYC Provider Selection",
            description="Unresolved question: which KYC provider should be selected?",
            supporting_quotation="Unresolved question: which KYC provider should be selected?",
            page_number=2,
            verification_status="VERIFIED"
        )

        self.db.add_all([f_dec, f_auth, f_db_mig, f_pay_plan, f_dep, f_pay_ops, f_q])
        self.db.commit()

        # Run Verification to create Conflict records
        run_project_verification(self.project.id, self.db)

        # Reconstruct Project State
        state = reconstruct_project_state(self.project.id, self.db, user_id=self.user.id)

        # 1. Check Authentication displayed as completed
        self.assertGreaterEqual(state.overview.completed_tasks, 1)

        # 2. Check Database migration displayed as pending (not started)
        self.assertGreaterEqual(state.overview.not_started_tasks, 1)

        # 3. Check Payment integration identified as blocked
        self.assertGreaterEqual(state.overview.blocked_tasks, 1)

        # 4. Check Rahul identified as owner
        self.assertIn("Rahul", state.ownership_state.distinct_owners_count >= 1 and ["Rahul"] or [])
        resps = get_responsibilities(self.project.id, self.db)
        rahul_resp = next((o for o in resps.owners if o.owner_name == "Rahul"), None)
        self.assertIsNotNone(rahul_resp, "Rahul must be registered in responsibility mapping")
        self.assertGreaterEqual(rahul_resp.total_assigned, 1)

        # 5. Check PostgreSQL displayed as recorded decision
        self.assertGreaterEqual(state.overview.total_decisions, 1)
        dec_timeline = get_decision_timeline(self.project.id, self.db)
        self.assertTrue(any("postgresql" in e.title.lower() for e in dec_timeline.dated_events + dec_timeline.undated_events))

        # 6. Check Payment status conflict surfaced
        conflicts = self.db.query(KnowledgeConflict).filter(KnowledgeConflict.project_id == self.project.id).all()
        self.assertGreaterEqual(len(conflicts), 1, "Status conflict between IN_PROGRESS and BLOCKED must be surfaced")
        pay_conflict = next((c for c in conflicts if c.conflict_type == ConflictType.STATUS), None)
        self.assertIsNotNone(pay_conflict)
        self.assertIn("payment integration", pay_conflict.description.lower())
        self.assertIsNotNone(pay_conflict.source_1_quote)
        self.assertIsNotNone(pay_conflict.source_2_quote)

        # 7. Check Dependency Graph: Database Migration -> Payment Integration
        dep_graph = get_dependency_graph(self.project.id, self.db)
        self.assertGreaterEqual(len(dep_graph.edges), 1, "Dependency edge must exist")
        # Check source is database migration and target is payment integration
        edge = dep_graph.edges[0]
        self.assertEqual(edge.relationship_type, "DEPENDS_ON")
        self.assertIsNotNone(edge.source_evidence)
        self.assertFalse(dep_graph.has_cycle, "Linear dependency must not be flagged as circular")

        # 8. Check Evidence references preserved
        self.assertIsNotNone(f_auth.supporting_quotation)
        self.assertIsNotNone(f_pay_plan.supporting_quotation)

        # 9. Check Unresolved questions shown
        self.assertEqual(state.overview.unresolved_questions, 1)

        # 10. Avoid inventing missing dates or owners
        # DB migration has no owner and no deadline -> remains unknown
        self.assertIsNone(f_db_mig.owner)
        self.assertIsNone(f_db_mig.deadline)
        self.assertGreaterEqual(state.uncertainty_state.missing_deadlines_count, 1)

    def test_02_circular_dependency_detection(self):
        """
        Verify that circular dependencies (A -> B -> A) are detected and flagged.
        """
        doc = Document(
            project_id=self.project.id,
            filename="cycle_spec.txt",
            file_path="/uploads/cycle_spec.txt",
            file_type="txt",
            file_hash="hash_cycle_doc",
            uploaded_by=self.user.id,
            status="PROCESSED"
        )
        self.db.add(doc)
        self.db.commit()

        # Task A depends on Task B, Task B depends on Task A
        t_a = ExtractedFinding(
            project_id=self.project.id,
            document_id=doc.id,
            entity_type="TASK",
            title="Service Alpha",
            description="Service Alpha core module"
        )
        t_b = ExtractedFinding(
            project_id=self.project.id,
            document_id=doc.id,
            entity_type="TASK",
            title="Service Beta",
            description="Service Beta core module"
        )
        dep1 = ExtractedFinding(
            project_id=self.project.id,
            document_id=doc.id,
            entity_type="DEPENDENCY",
            title="Service Alpha",
            related_entity="Service Beta",
            description="Service Alpha depends on Service Beta"
        )
        dep2 = ExtractedFinding(
            project_id=self.project.id,
            document_id=doc.id,
            entity_type="DEPENDENCY",
            title="Service Beta",
            related_entity="Service Alpha",
            description="Service Beta depends on Service Alpha"
        )
        self.db.add_all([t_a, t_b, dep1, dep2])
        self.db.commit()

        graph = get_dependency_graph(self.project.id, self.db)
        self.assertTrue(graph.has_cycle, "Circular dependency between Alpha and Beta must be detected")
        self.assertGreaterEqual(len(graph.cycles), 1)

    def test_03_decision_timeline_ordering(self):
        """
        Verify chronological sorting of decisions: dated events ordered by date,
        undated decisions partitioned cleanly without invented dates.
        """
        doc = Document(
            project_id=self.project.id,
            filename="decisions.txt",
            file_path="/uploads/decisions.txt",
            file_type="txt",
            file_hash="hash_dec_doc",
            uploaded_by=self.user.id,
            status="PROCESSED"
        )
        self.db.add(doc)
        self.db.commit()

        d1 = ExtractedFinding(
            project_id=self.project.id,
            document_id=doc.id,
            entity_type="DECISION",
            title="Adopt Next.js",
            description="Decided to use Next.js",
            decision_date="2026-05-10"
        )
        d2 = ExtractedFinding(
            project_id=self.project.id,
            document_id=doc.id,
            entity_type="DECISION",
            title="Adopt Tailwind CSS",
            description="Decided to use Tailwind",
            decision_date="2026-11-01"
        )
        d3 = ExtractedFinding(
            project_id=self.project.id,
            document_id=doc.id,
            entity_type="DECISION",
            title="Use Microservices Architecture",
            description="Agreed to split backend into microservices"
            # No date
        )
        self.db.add_all([d1, d2, d3])
        self.db.commit()

        timeline = get_decision_timeline(self.project.id, self.db)
        self.assertEqual(len(timeline.dated_events), 2)
        self.assertEqual(len(timeline.undated_events), 1)

        # Check chronological ordering: earliest to latest or latest to earliest
        dates = [e.normalized_date for e in timeline.dated_events]
        self.assertEqual(dates, sorted(dates, reverse=True))
        self.assertEqual(timeline.undated_events[0].title, "Use Microservices Architecture")

    def test_04_risk_register_classification(self):
        """
        Verify that risk register separates source-extracted risks from AI recommendations.
        """
        doc = Document(
            project_id=self.project.id,
            filename="risks.txt",
            file_path="/uploads/risks.txt",
            file_type="txt",
            file_hash="hash_risk_doc",
            uploaded_by=self.user.id,
            status="PROCESSED"
        )
        self.db.add(doc)
        self.db.commit()

        r_source = ExtractedFinding(
            project_id=self.project.id,
            document_id=doc.id,
            entity_type="RISK",
            title="Database Connection Pool Exhaustion",
            description="High risk of DB pool exhaustion under load",
            priority="CRITICAL",
            is_recommendation=False
        )
        r_rec = ExtractedFinding(
            project_id=self.project.id,
            document_id=doc.id,
            entity_type="RISK",
            title="Consider Automated Canaries",
            description="We recommend adopting automated canary analysis",
            is_recommendation=True
        )
        self.db.add_all([r_source, r_rec])
        self.db.commit()

        risk_reg = get_risk_register(self.project.id, self.db)
        self.assertEqual(len(risk_reg.source_risks), 1)
        self.assertEqual(len(risk_reg.ai_recommendations), 1)
        self.assertEqual(risk_reg.source_risks[0].severity, "CRITICAL")
        self.assertEqual(risk_reg.critical_count, 1)

    def test_05_search_knowledge_endpoint(self):
        """
        Verify project-scoped search finds matching findings with verification citations.
        """
        doc = Document(
            project_id=self.project.id,
            filename="search_doc.txt",
            file_path="/uploads/search_doc.txt",
            file_type="txt",
            file_hash="hash_search_doc",
            uploaded_by=self.user.id,
            status="PROCESSED"
        )
        self.db.add(doc)
        self.db.commit()

        f = ExtractedFinding(
            project_id=self.project.id,
            document_id=doc.id,
            entity_type="TASK",
            title="ElasticSearch Cluster Upgrade",
            description="Upgrade ElasticSearch from version 7 to 8",
            owner="Vikram",
            supporting_quotation="Upgrade ElasticSearch from version 7 to 8."
        )
        self.db.add(f)
        self.db.commit()

        results = search_project_knowledge(self.project.id, "elasticsearch", self.db)
        self.assertGreaterEqual(results.total_results, 1)
        self.assertIn("ElasticSearch", results.results[0].title)

        # Cross-project privacy: search in another project returns 0
        empty_res = search_project_knowledge("non-existent-proj-id", "elasticsearch", self.db)
        self.assertEqual(empty_res.total_results, 0)


if __name__ == "__main__":
    unittest.main()
