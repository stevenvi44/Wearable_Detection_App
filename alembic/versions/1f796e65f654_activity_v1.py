"""activity  v1

Revision ID: 1f796e65f654
Revises: 583f9b45e682
Create Date: 2025-12-13 03:31:16.324377

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1f796e65f654'
down_revision: Union[str, Sequence[str], None] = '583f9b45e682'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Table activity_daily has been removed, skip migration
    pass


def downgrade() -> None:
    """Downgrade schema."""
    # Table activity_daily has been removed, skip migration
    pass
