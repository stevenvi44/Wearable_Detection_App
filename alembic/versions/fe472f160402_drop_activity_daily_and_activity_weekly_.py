"""drop_activity_daily_and_activity_weekly_tables

Revision ID: fe472f160402
Revises: 0665aaf05f2a
Create Date: 2025-12-14 23:29:01.643809

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = 'fe472f160402'
down_revision: Union[str, Sequence[str], None] = '0665aaf05f2a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Drop activity_weekly and activity_daily tables if they exist
    conn = op.get_bind()
    inspector = inspect(conn)
    tables = inspector.get_table_names()
    
    if 'activity_weekly' in tables:
        op.drop_table('activity_weekly')
    
    if 'activity_daily' in tables:
        op.drop_table('activity_daily')


def downgrade() -> None:
    """Downgrade schema."""
    # Note: We don't recreate these tables in downgrade as they're no longer needed
    pass
