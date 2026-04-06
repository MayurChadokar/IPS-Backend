"""Add Meritto CRM Sync Audit table for tracking sync attempts

Revision ID: meritto_crm_sync_audit
Revises: 2703c5092f11
Create Date: 2026-04-06

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'meritto_crm_sync_audit'
down_revision = '2703c5092f11'
branch_labels = None
depends_on = None


def upgrade():
    # Create CRM Sync Audit table
    op.create_table(
        'meritto_crm_sync_audit',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('entity_type', sa.String(50), nullable=False, comment='Type: inquiry, contact'),
        sa.Column('entity_id', sa.Integer(), nullable=False, comment='ID of the inquiry or contact'),
        sa.Column('entity_email', sa.String(255), nullable=False),
        sa.Column('entity_name', sa.String(255), nullable=False),
        sa.Column('college_name', sa.String(255), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, 
                 comment='pending, success, failed, retrying'),
        sa.Column('attempt_count', sa.Integer(), nullable=False, default=0),
        sa.Column('last_attempt_at', sa.DateTime(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('response_data', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, 
                 server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False,
                 server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('idx_meritto_entity_type_id', 'entity_type', 'entity_id'),
        sa.Index('idx_meritto_status', 'status'),
        sa.Index('idx_meritto_email', 'entity_email'),
        sa.Index('idx_meritto_created_at', 'created_at'),
    )


def downgrade():
    op.drop_table('meritto_crm_sync_audit')
