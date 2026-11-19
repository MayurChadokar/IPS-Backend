"""add ambition mic submissions

Revision ID: 91c4d8e2f7a1
Revises: 7a3c2d9f1b60
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "91c4d8e2f7a1"
down_revision: Union[str, None] = "7a3c2d9f1b60"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ambition_mic_submissions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("full_name", sa.String(length=150), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("phone_number", sa.String(length=20), nullable=False),
        sa.Column("city", sa.String(length=100), nullable=False),
        sa.Column("education_level", sa.String(length=100), nullable=False),
        sa.Column("institution_name", sa.String(length=255), nullable=False),
        sa.Column("video_path", sa.String(length=500), nullable=False),
        sa.Column("video_original_name", sa.String(length=255), nullable=False),
        sa.Column("video_content_type", sa.String(length=100), nullable=False),
        sa.Column("video_size", sa.Integer(), nullable=False),
        sa.Column("email_status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("email_error", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"), mysql_engine="InnoDB", mysql_charset="utf8mb4",
    )
    op.create_index(op.f("ix_ambition_mic_submissions_id"), "ambition_mic_submissions", ["id"], unique=False)
    op.create_index(op.f("ix_ambition_mic_submissions_email"), "ambition_mic_submissions", ["email"], unique=False)
    op.create_index("ix_ambition_mic_submissions_created_at", "ambition_mic_submissions", ["created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_ambition_mic_submissions_created_at", table_name="ambition_mic_submissions")
    op.drop_index(op.f("ix_ambition_mic_submissions_email"), table_name="ambition_mic_submissions")
    op.drop_index(op.f("ix_ambition_mic_submissions_id"), table_name="ambition_mic_submissions")
    op.drop_table("ambition_mic_submissions")
