import os
import fitz
import docx

def create_sample_files(target_dir: str):
    os.makedirs(target_dir, exist_ok=True)

    # 1. Apollo Architecture Decisions (PDF)
    pdf_path = os.path.join(target_dir, "Apollo_Architecture_Decisions.pdf")
    doc = fitz.open()

    # Page 1
    page1 = doc.new_page()
    text1 = """APOLLO CORE ARCHITECTURE - DECISION RECORD (ADR)
Document Version: 2.4 | Status: Approved
Project: Apollo Knowledge Continuity

SECTION 1: CORE ARCHITECTURAL CHOICES
We decided to adopt an event-driven microservices architecture using Apache Kafka for real-time order processing.
ADR-01: We chose PostgreSQL with pgvector as our primary analytical datastore to enable semantic search over transaction logs.
Architectural Decision: All microservices must implement OpenTelemetry distributed tracing and export metrics to Prometheus.
The team agreed to deprecate legacy RabbitMQ clusters by end of Q2 2026.
Contact person for architecture sign-off is Elena Rostova (elena.rostova@apollo.corp).

SECTION 2: STORAGE & MIGRATIONS
Task: Database schema migrations must run strictly through Alembic version control before Kubernetes rollout.
Responsible: Marcus Chen is responsible for the Alembic migration scripts and rollback plans.
Deadline: The database migration dry-run is scheduled by April 15, 2026.
"""
    page1.insert_text((50, 50), text1, fontsize=11)

    # Page 2
    page2 = doc.new_page()
    text2 = """SECTION 3: DEPENDENCIES & SYSTEM COUPLINGS
Dependency: Apollo payment gateway relies on the third-party Stripe API v2024-06-20 webhooks.
Dependency: User authentication depends on an upstream Okta OAuth2 SSO identity provider.
Risk: There is an active risk of token throttling during Black Friday peak traffic if Stripe rate limits are exceeded.
Mitigation: Marcus Chen will implement an exponential backoff circuit breaker with Redis token bucket caching.

SECTION 4: UNRESOLVED QUESTIONS
Unresolved Question: What is the failover strategy if the multi-region Kafka cluster experiences an split-brain partition?
Open question: TBD whether to support GraphQL subscriptions or maintain pure WebSocket streams for client events.
"""
    page2.insert_text((50, 50), text2, fontsize=11)
    doc.save(pdf_path)
    doc.close()

    # 2. Apollo Handover Notes (DOCX)
    docx_path = os.path.join(target_dir, "Apollo_Handover_Notes.docx")
    d_doc = docx.Document()
    d_doc.add_heading("Project Apollo - Outgoing Engineer Handover Dossier", level=1)
    d_doc.add_paragraph("Author: Sarah Jenkins (Lead Backend Engineer) | Outgoing Date: May 2026")
    
    d_doc.add_heading("1. Current Delivery Status & Milestones", level=2)
    d_doc.add_paragraph("Milestone: Phase 1 Payment Gateway Integration was completed and launched on February 10, 2026.")
    d_doc.add_paragraph("Milestone: GA Release target is officially locked for June 30, 2026.")
    d_doc.add_paragraph("Action item: Incoming engineer must rotate all AWS IAM access keys upon handover completion.")

    d_doc.add_heading("2. Pending Tasks & Accountabilities", level=2)
    d_doc.add_paragraph("Task: Finalize end-to-end integration tests for asynchronous webhook settlement.")
    d_doc.add_paragraph("Responsible: Sarah Jenkins was leading this task; reassigning to Incoming Member.")
    d_doc.add_paragraph("Deadline: The test suite must be merged before May 20, 2026.")
    d_doc.add_paragraph("Critical Blocker: CI/CD deployment pipeline is currently blocked by failing Docker socket permissions on GitHub Actions runner.")

    d_doc.add_heading("3. Key Team Contacts", level=2)
    d_doc.add_paragraph("Team lead: Alex Rivera (alex.rivera@apollo.corp) - engineering director.")
    d_doc.add_paragraph("DevOps contact: Liam Vance (liam.vance@apollo.corp) - infrastructure & Kubernetes cluster admin.")
    d_doc.save(docx_path)

    # 3. Sprint 24 Blockers and Risks (TXT)
    txt_path = os.path.join(target_dir, "Sprint_24_Blockers_and_Risks.txt")
    txt_content = """SPRINT 24 POST-MORTEM & RISK LOG
Project: Apollo Ingestion Engine
Date: March 2026

1. CRITICAL BLOCKERS:
- Blocker: Database connection pool exhaustion under load testing is blocking QA sign-off.
- Blocker: Blocked by security team review for external data egress compliance.
- Owner is Sarah Jenkins for database pool tuning.

2. CONFLICTING DEADLINES FOR INVESTIGATION:
- Deadline: The test suite must be merged before May 30, 2026. (Note: conflicts with May 20 deadline in handover doc)
- Target delivery deadline for SOC2 audit submission is June 15, 2026.

3. RESILIENCE RISKS:
- Risk: Memory leak identified in websocket subscriber thread pool during sustained client disconnects.
- Risk: Single point of failure in background Redis worker node without Sentinel replication.

4. NEXT ACTIONS:
- Action item: Refactor connection pool max overflow parameter from 10 to 50 in database.py.
- Action item: Incoming engineer should pair with Liam Vance on Redis Sentinel failover testing.
"""
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(txt_content)

    print("Sample documents generated successfully at:", target_dir)

if __name__ == "__main__":
    create_sample_files("sample_documents")
