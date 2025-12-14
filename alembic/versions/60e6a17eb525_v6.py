"""v6

Revision ID: 60e6a17eb525
Revises: fe472f160402
Create Date: 2025-12-14 23:33:06.029921

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '60e6a17eb525'
down_revision: Union[str, Sequence[str], None] = 'fe472f160402'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
