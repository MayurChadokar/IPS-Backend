"""add social and club activity types

Revision ID: a1b2c3d4e5f6
Revises: 0d141484e21d
Create Date: 2026-07-14 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '0d141484e21d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # MySQL: modify ENUM column to include new values SOCIAL and CLUB
    op.execute(
        "ALTER TABLE activities MODIFY COLUMN activity_type "
        "ENUM('CULTURAL', 'EVENT_CELEBRATION', 'WORKSHOP', 'SOCIAL', 'CLUB') NOT NULL"
    )


def downgrade() -> None:
    # Revert back to original 3 enum values
    # WARNING: Any rows with 'SOCIAL' or 'CLUB' must be removed/updated first
    op.execute(
        "ALTER TABLE activities MODIFY COLUMN activity_type "
        "ENUM('CULTURAL', 'EVENT_CELEBRATION', 'WORKSHOP') NOT NULL"
    )
