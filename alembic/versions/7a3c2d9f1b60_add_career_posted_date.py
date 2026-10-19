"""Add an editable posting date to career openings.

Revision ID: 7a3c2d9f1b60
Revises: 6f2e9d1c8a40
"""
from alembic import op
import sqlalchemy as sa


revision = "7a3c2d9f1b60"
down_revision = "6f2e9d1c8a40"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("career_openings", sa.Column("posted_date", sa.Date(), nullable=True))
    openings = sa.table(
        "career_openings", sa.column("posted_date", sa.Date()),
        sa.column("created_at", sa.DateTime()),
    )
    # Preserve the existing calendar date until an admin chooses a different one.
    op.execute(openings.update().where(openings.c.posted_date.is_(None)).values(posted_date=sa.func.date(openings.c.created_at)))
    with op.batch_alter_table("career_openings") as batch:
        batch.alter_column("posted_date", existing_type=sa.Date(), nullable=False)


def downgrade():
    with op.batch_alter_table("career_openings") as batch:
        batch.drop_column("posted_date")
