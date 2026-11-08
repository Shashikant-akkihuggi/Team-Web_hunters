"""phase5 knowledge reconstruction

Revision ID: 005_phase5_knowledge_reconstruction
Revises: 004_phase4_ai_knowledge_engine
Create Date: 2026-11-08 23:45:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '005_phase5_knowledge_reconstruction'
down_revision = '004_phase4_ai_knowledge_engine'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # 1. Add columns to projects table
    project_cols = [
        ('last_reconstructed_at', sa.Column('last_reconstructed_at', sa.DateTime(), nullable=True)),
        ('reconstruction_version', sa.Column('reconstruction_version', sa.Integer(), nullable=True, server_default='1')),
    ]
    for col_name, col_def in project_cols:
        try:
            op.add_column('projects', col_def)
        except Exception:
            pass

    # 2. Create project_reconstructions table if not exists
    try:
        op.create_table(
            'project_reconstructions',
            sa.Column('id', sa.String(length=36), primary_key=True),
            sa.Column('project_id', sa.String(length=36), sa.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False),
            sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
            sa.Column('extraction_job_id', sa.String(length=36), sa.ForeignKey('extraction_jobs.id', ondelete='SET NULL'), nullable=True),
            sa.Column('overview_json', sa.JSON(), nullable=False),
            sa.Column('dependency_graph_json', sa.JSON(), nullable=True),
            sa.Column('risk_register_json', sa.JSON(), nullable=True),
            sa.Column('responsibilities_json', sa.JSON(), nullable=True),
            sa.Column('freshness_status', sa.String(length=50), nullable=False, server_default='UP_TO_DATE'),
            sa.Column('reconstructed_by', sa.String(length=36), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True),
        )
    except Exception:
        pass

def downgrade() -> None:
    try:
        op.drop_table('project_reconstructions')
    except Exception:
        pass
