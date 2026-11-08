"""phase4 ai knowledge engine

Revision ID: 004_phase4_ai_knowledge_engine
Revises: 003_phase3_document_pipeline
Create Date: 2026-11-08 23:30:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '004_phase4_ai_knowledge_engine'
down_revision = '003_phase3_document_pipeline'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # 1. Add columns to extracted_findings table
    finding_cols = [
        ('chunk_id', sa.Column('chunk_id', sa.String(36), sa.ForeignKey('document_chunks.id', ondelete='SET NULL'), nullable=True)),
        ('task_status', sa.Column('task_status', sa.String(50), nullable=True)),
        ('priority', sa.Column('priority', sa.String(50), nullable=True)),
        ('decided_by', sa.Column('decided_by', sa.String(255), nullable=True)),
        ('decision_date', sa.Column('decision_date', sa.String(100), nullable=True)),
        ('impact', sa.Column('impact', sa.Text(), nullable=True)),
        ('likelihood', sa.Column('likelihood', sa.String(50), nullable=True)),
        ('mitigation', sa.Column('mitigation', sa.Text(), nullable=True)),
        ('related_entity', sa.Column('related_entity', sa.String(255), nullable=True)),
    ]
    for col_name, col_def in finding_cols:
        try:
            op.add_column('extracted_findings', col_def)
        except Exception:
            pass

    # 2. Create extraction_jobs table if not exists
    try:
        op.create_table(
            'extraction_jobs',
            sa.Column('id', sa.String(length=36), primary_key=True),
            sa.Column('project_id', sa.String(length=36), sa.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False),
            sa.Column('status', sa.String(length=50), nullable=False, server_default='QUEUED'),
            sa.Column('processed_documents_count', sa.Integer(), server_default='0'),
            sa.Column('processed_chunks_count', sa.Integer(), server_default='0'),
            sa.Column('extracted_findings_count', sa.Integer(), server_default='0'),
            sa.Column('conflicts_count', sa.Integer(), server_default='0'),
            sa.Column('unsupported_count', sa.Integer(), server_default='0'),
            sa.Column('error_message', sa.Text(), nullable=True),
            sa.Column('created_by', sa.String(length=36), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.Column('updated_at', sa.DateTime(), nullable=True),
            sa.Column('completed_at', sa.DateTime(), nullable=True),
        )
    except Exception:
        pass

    # 3. Create knowledge_conflicts table if not exists
    try:
        op.create_table(
            'knowledge_conflicts',
            sa.Column('id', sa.String(length=36), primary_key=True),
            sa.Column('project_id', sa.String(length=36), sa.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False),
            sa.Column('finding_id_1', sa.String(length=36), sa.ForeignKey('extracted_findings.id', ondelete='CASCADE'), nullable=True),
            sa.Column('finding_id_2', sa.String(length=36), sa.ForeignKey('extracted_findings.id', ondelete='CASCADE'), nullable=True),
            sa.Column('conflict_type', sa.String(length=50), nullable=False, server_default='STATUS'),
            sa.Column('description', sa.Text(), nullable=False),
            sa.Column('source_1_quote', sa.Text(), nullable=True),
            sa.Column('source_1_page', sa.Integer(), nullable=True),
            sa.Column('source_1_doc_id', sa.String(length=36), nullable=True),
            sa.Column('source_2_quote', sa.Text(), nullable=True),
            sa.Column('source_2_page', sa.Integer(), nullable=True),
            sa.Column('source_2_doc_id', sa.String(length=36), nullable=True),
            sa.Column('status', sa.String(length=50), nullable=False, server_default='OPEN'),
            sa.Column('created_at', sa.DateTime(), nullable=True),
        )
    except Exception:
        pass

def downgrade() -> None:
    try:
        op.drop_table('knowledge_conflicts')
    except Exception:
        pass
    try:
        op.drop_table('extraction_jobs')
    except Exception:
        pass
