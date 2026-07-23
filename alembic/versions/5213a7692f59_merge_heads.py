"""merge heads

Revision ID: 5213a7692f59
Revises: 22cfdbf0360d, a1b2c3d4e5f6
Create Date: 2026-07-16 12:12:42.123751

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5213a7692f59'
down_revision: Union[str, None] = ('22cfdbf0360d', 'a1b2c3d4e5f6')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
