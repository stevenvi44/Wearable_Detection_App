"""activity  v2

Revision ID: 1f9e768dc710
Revises: 1f796e65f654
Create Date: 2025-12-13 03:51:47.465273

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1f9e768dc710'
down_revision: Union[str, Sequence[str], None] = '1f796e65f654'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # Table activity_weekly has been removed, skip migration
    pass


def downgrade() -> None:
    """Downgrade schema."""
    # Table activity_weekly has been removed, skip migration
    pass
