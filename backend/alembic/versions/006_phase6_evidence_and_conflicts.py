"""phase6 evidence and conflicts

Revision ID: 006_phase6_evidence_and_conflicts
Revises: 005_phase5_knowledge_reconstruction
Create Date: 2026-11-09 00:15:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '006_phase6_evidence_and_conflicts'
down_revision = '005_phase5_knowledge_reconstruction'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # 1. Add columns to evidence_references
    evidence_cols = [
        ('document_filename', sa.Column('document_filename', sa.String(length=255), nullable=True)),
        ('chunk_id', sa.Column('chunk_id', sa.String(length=36), sa.ForeignKey('document_chunks.id', ondelete='SET NULL'), nullable=True)),
        ('page_end', sa.Column('page_end', sa.Integer(), nullable=True, server_default='1')),
        ('character_start', sa.Column('character_start', sa.Integer(), nullable=True, server_default='0')),
        ('character_end', sa.Column('character_end', sa.Integer(), nullable=True, server_default='0')),
        ('verification_status', sa.Column('verification_status', sa.String(length=50), nullable=True, server_default='VERIFIED')),
        ('verification_method', sa.Column('verification_method', sa.String(length=50), nullable=True, server_default='EXACT_SUBSTRING')),
        ('verification_timestamp', sa.Column('verification_timestamp', sa.DateTime(), nullable=True)),
    ]
    for col_name, col_def in evidence_cols:
        try:
            op.add_column('evidence_references', col_def)
        except Exception:
            pass

    # 2. Add columns to knowledge_conflicts
    conflict_cols = [
        ('title', sa.Column('title', sa.String(length=255), nullable=True)),
        ('related_entity_type', sa.Column('related_entity_type', sa.String(length=50), nullable=True)),
        ('related_entity_id', sa.Column('related_entity_id', sa.String(length=255), nullable=True)),
        ('finding_a_id', sa.Column('finding_a_id', sa.String(length=36), sa.ForeignKey('extracted_findings.id', ondelete='CASCADE'), nullable=True)),
        ('finding_b_id', sa.Column('finding_b_id', sa.String(length=36), sa.ForeignKey('extracted_findings.id', ondelete='CASCADE'), nullable=True)),
        ('evidence_a_id', sa.Column('evidence_a_id', sa.String(length=36), sa.ForeignKey('evidence_references.id', ondelete='SET NULL'), nullable=True)),
        ('evidence_b_id', sa.Column('evidence_b_id', sa.String(length=36), sa.ForeignKey('evidence_references.id', ondelete='SET NULL'), nullable=True)),
        ('conflict_status', sa.Column('conflict_status', sa.String(length=50), nullable=True, server_default='OPEN')),
        ('severity', sa.Column('severity', sa.String(length=50), nullable=True, server_default='MEDIUM')),
        ('detected_at', sa.Column('detected_at', sa.DateTime(), nullable=True)),
        ('resolved_at', sa.Column('resolved_at', sa.DateTime(), nullable=True)),
        ('resolved_by', sa.Column('resolved_by', sa.String(length=36), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)),
        ('resolution_choice', sa.Column('resolution_choice', sa.String(length=50), nullable=True)),
        ('resolution_notes', sa.Column('resolution_notes', sa.Text(), nullable=True)),
        ('updated_at', sa.Column('updated_at', sa.DateTime(), nullable=True)),
    ]
    for col_name, col_def in conflict_cols:
        try:
            op.add_column('knowledge_conflicts', col_def)
        except Exception:
            pass

def downgrade() -> None:
    pass
