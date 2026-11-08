"""phase3 document pipeline

Revision ID: 003_phase3_document_pipeline
Revises: 002_phase2_projects_and_members
Create Date: 2026-11-08 23:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '003_phase3_document_pipeline'
down_revision = '002_phase2_projects_and_members'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # 1. Add columns to documents table
    doc_cols = [
        ('original_filename', sa.Column('original_filename', sa.String(255), nullable=True)),
        ('storage_key', sa.Column('storage_key', sa.String(512), nullable=True)),
        ('mime_type', sa.Column('mime_type', sa.String(100), nullable=True)),
        ('file_extension', sa.Column('file_extension', sa.String(20), nullable=True)),
        ('checksum', sa.Column('checksum', sa.String(64), nullable=True)),
        ('processing_status', sa.Column('processing_status', sa.String(50), nullable=True, server_default='UPLOADED')),
        ('extracted_character_count', sa.Column('extracted_character_count', sa.Integer(), nullable=True, server_default='0')),
        ('chunk_count', sa.Column('chunk_count', sa.Integer(), nullable=True, server_default='0')),
        ('processing_error', sa.Column('processing_error', sa.Text(), nullable=True)),
        ('updated_at', sa.Column('updated_at', sa.DateTime(), nullable=True)),
        ('processed_at', sa.Column('processed_at', sa.DateTime(), nullable=True)),
    ]
    for col_name, col_def in doc_cols:
        try:
            op.add_column('documents', col_def)
        except Exception:
            pass

    # 2. Add columns to document_chunks table
    chunk_cols = [
        ('page_start', sa.Column('page_start', sa.Integer(), nullable=True, server_default='1')),
        ('page_end', sa.Column('page_end', sa.Integer(), nullable=True, server_default='1')),
        ('character_start', sa.Column('character_start', sa.Integer(), nullable=True, server_default='0')),
        ('character_end', sa.Column('character_end', sa.Integer(), nullable=True, server_default='0')),
    ]
    for col_name, col_def in chunk_cols:
        try:
            op.add_column('document_chunks', col_def)
        except Exception:
            pass

    # 3. Create document_pages table if not exists
    try:
        op.create_table(
            'document_pages',
            sa.Column('id', sa.String(length=36), primary_key=True),
            sa.Column('document_id', sa.String(length=36), sa.ForeignKey('documents.id', ondelete='CASCADE'), nullable=False),
            sa.Column('project_id', sa.String(length=36), sa.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False),
            sa.Column('page_number', sa.Integer(), nullable=False),
            sa.Column('extracted_text', sa.Text(), nullable=False),
            sa.Column('char_count', sa.Integer(), default=0),
            sa.Column('created_at', sa.DateTime(), nullable=True),
        )
    except Exception:
        pass

def downgrade() -> None:
    try:
        op.drop_table('document_pages')
    except Exception:
        pass
