"""add user access scope

Revision ID: b7e3a9f01234
Revises: 91c4d8e2f7a1
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b7e3a9f01234"
down_revision: Union[str, None] = "91c4d8e2f7a1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("access_scope", sa.String(length=50), nullable=True))
    op.create_index(op.f("ix_users_access_scope"), "users", ["access_scope"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_users_access_scope"), table_name="users")
    op.drop_column("users", "access_scope")
