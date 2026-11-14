"""expand_import_and_data_acquisition

Revision ID: f585e5963394
Revises: 20c1c10ddc96
Create Date: 2026-11-14 06:48:36.560699

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'f585e5963394'
down_revision: Union[str, None] = '20c1c10ddc96'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Expand import_jobs
    op.add_column('import_jobs', sa.Column('account_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('accounts.id', ondelete='SET NULL'), nullable=True))
    op.add_column('import_jobs', sa.Column('original_filename', sa.String(length=255), nullable=True))
    op.add_column('import_jobs', sa.Column('storage_reference', sa.String(length=512), nullable=True))
    op.add_column('import_jobs', sa.Column('file_checksum', sa.String(length=64), nullable=True))
    op.add_column('import_jobs', sa.Column('file_size', sa.Integer(), nullable=True))
    op.add_column('import_jobs', sa.Column('mime_type', sa.String(length=100), nullable=True))
    op.add_column('import_jobs', sa.Column('valid_records', sa.Integer(), server_default='0', nullable=False))
    op.add_column('import_jobs', sa.Column('invalid_records', sa.Integer(), server_default='0', nullable=False))
    op.add_column('import_jobs', sa.Column('duplicate_records', sa.Integer(), server_default='0', nullable=False))
    op.add_column('import_jobs', sa.Column('imported_records', sa.Integer(), server_default='0', nullable=False))
    op.add_column('import_jobs', sa.Column('processing_metadata', postgresql.JSONB(astext_type=sa.Text()), server_default='{}', nullable=False))
    op.add_column('import_jobs', sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True))

    op.create_index('ix_import_jobs_status', 'import_jobs', ['status'])
    op.create_index('ix_import_jobs_account_id', 'import_jobs', ['account_id'])
    op.create_index('ix_import_jobs_file_checksum', 'import_jobs', ['file_checksum'])

    # 2. Create import_batches
    op.create_table(
        'import_batches',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('import_job_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('import_jobs.id', ondelete='CASCADE'), nullable=False),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('workspaces.id', ondelete='CASCADE'), nullable=False),
        sa.Column('source_format', sa.String(length=30), nullable=False),
        sa.Column('sheet_name', sa.String(length=100), nullable=True),
        sa.Column('row_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('valid_row_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('invalid_row_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('duplicate_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('processing_status', sa.String(length=30), server_default='extracted', nullable=False),
        sa.Column('column_mapping', postgresql.JSONB(astext_type=sa.Text()), server_default='{}', nullable=False),
        sa.Column('opening_balance', sa.Numeric(precision=18, scale=4), nullable=True),
        sa.Column('closing_balance', sa.Numeric(precision=18, scale=4), nullable=True),
        sa.Column('calculated_closing_balance', sa.Numeric(precision=18, scale=4), nullable=True),
        sa.Column('reconciliation_difference', sa.Numeric(precision=18, scale=4), nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), server_default='{}', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
    )
    op.create_index('ix_import_batches_import_job_id', 'import_batches', ['import_job_id'])
    op.create_index('ix_import_batches_workspace_id', 'import_batches', ['workspace_id'])

    # 3. Create import_candidates
    op.create_table(
        'import_candidates',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('import_batch_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('import_batches.id', ondelete='CASCADE'), nullable=False),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('workspaces.id', ondelete='CASCADE'), nullable=False),
        sa.Column('account_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('accounts.id', ondelete='SET NULL'), nullable=True),
        sa.Column('source_row_number', sa.Integer(), nullable=False),
        sa.Column('raw_data', postgresql.JSONB(astext_type=sa.Text()), server_default='{}', nullable=False),
        sa.Column('normalized_data', postgresql.JSONB(astext_type=sa.Text()), server_default='{}', nullable=False),
        sa.Column('validation_status', sa.String(length=30), server_default='valid', nullable=False),
        sa.Column('validation_errors', postgresql.JSONB(astext_type=sa.Text()), server_default='[]', nullable=False),
        sa.Column('duplicate_status', sa.String(length=30), server_default='none', nullable=False),
        sa.Column('duplicate_match_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('transactions.id', ondelete='SET NULL'), nullable=True),
        sa.Column('duplicate_reason', sa.Text(), nullable=True),
        sa.Column('confidence_score', sa.Numeric(precision=4, scale=2), server_default='1.00', nullable=False),
        sa.Column('review_status', sa.String(length=30), server_default='pending', nullable=False),
        sa.Column('selected_for_import', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('created_transaction_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('transactions.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
    )
    op.create_index('ix_import_candidates_batch_id', 'import_candidates', ['import_batch_id'])
    op.create_index('ix_import_candidates_workspace_id', 'import_candidates', ['workspace_id'])
    op.create_index('ix_import_candidates_account_id', 'import_candidates', ['account_id'])
    op.create_index('ix_import_candidates_validation_status', 'import_candidates', ['validation_status'])
    op.create_index('ix_import_candidates_duplicate_status', 'import_candidates', ['duplicate_status'])
    op.create_index('ix_import_candidates_review_status', 'import_candidates', ['review_status'])
    op.create_index('ix_import_candidates_created_tx', 'import_candidates', ['created_transaction_id'])


def downgrade() -> None:
    op.drop_table('import_candidates')
    op.drop_table('import_batches')

    op.drop_index('ix_import_jobs_file_checksum', table_name='import_jobs')
    op.drop_index('ix_import_jobs_account_id', table_name='import_jobs')
    op.drop_index('ix_import_jobs_status', table_name='import_jobs')

    op.drop_column('import_jobs', 'completed_at')
    op.drop_column('import_jobs', 'processing_metadata')
    op.drop_column('import_jobs', 'imported_records')
    op.drop_column('import_jobs', 'duplicate_records')
    op.drop_column('import_jobs', 'invalid_records')
    op.drop_column('import_jobs', 'valid_records')
    op.drop_column('import_jobs', 'mime_type')
    op.drop_column('import_jobs', 'file_size')
    op.drop_column('import_jobs', 'file_checksum')
    op.drop_column('import_jobs', 'storage_reference')
    op.drop_column('import_jobs', 'original_filename')
    op.drop_column('import_jobs', 'account_id')
