"""phase2 projects and members

Revision ID: 002_phase2_projects_and_members
Revises: 001_initial_schema
Create Date: 2026-11-08 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '002_phase2_projects_and_members'
down_revision = '001_initial_schema'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Add category, start_date, expected_completion_date to projects
    try:
        op.add_column('projects', sa.Column('category', sa.String(length=100), nullable=True, server_default='Engineering'))
    except Exception:
        pass

    try:
        op.add_column('projects', sa.Column('start_date', sa.DateTime(), nullable=True))
    except Exception:
        pass

    try:
        op.add_column('projects', sa.Column('expected_completion_date', sa.DateTime(), nullable=True))
    except Exception:
        pass

    # Create unique constraint on project_members (project_id, user_id)
    try:
        op.create_unique_constraint('uq_project_user', 'project_members', ['project_id', 'user_id'])
    except Exception:
        pass

def downgrade() -> None:
    try:
        op.drop_constraint('uq_project_user', 'project_members', type_='unique')
    except Exception:
        pass

    try:
        op.drop_column('projects', 'expected_completion_date')
        op.drop_column('projects', 'start_date')
        op.drop_column('projects', 'category')
    except Exception:
        pass
