"""create_activity_tables_if_missing

Revision ID: 4e5f62b9bf3b
Revises: 1f9e768dc710
Create Date: 2025-12-13 22:30:43.216747

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = '4e5f62b9bf3b'
down_revision: Union[str, Sequence[str], None] = '1f9e768dc710'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Removed automatic creation of activity_daily and activity_weekly tables
    pass


def downgrade() -> None:
    """Downgrade schema."""
    # Removed automatic dropping of activity_daily and activity_weekly tables
    pass
