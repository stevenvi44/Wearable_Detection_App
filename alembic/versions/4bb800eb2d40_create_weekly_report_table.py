"""create_weekly_report_table

Revision ID: 4bb800eb2d40
Revises: 4e5f62b9bf3b
Create Date: 2025-12-14 02:43:24.000847

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = '4bb800eb2d40'
down_revision: Union[str, Sequence[str], None] = '4e5f62b9bf3b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Check if weekly_report table exists, create if not
    conn = op.get_bind()
    inspector = inspect(conn)
    tables = inspector.get_table_names()
    
    if 'weekly_report' not in tables:
        op.create_table(
            'weekly_report',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=True),
            sa.Column('activity_date', sa.Date(), nullable=False),
            sa.Column('average_steps', sa.Integer(), nullable=True),
            sa.Column('most_active_day', sa.String(length=20), nullable=True),
            sa.Column('total_distance_km', sa.Float(), nullable=True),
            sa.Column('calories_burned', sa.Integer(), nullable=True),
            sa.Column('created_at', sa.TIMESTAMP(), nullable=True),
            sa.ForeignKeyConstraint(['user_id'], ['users.user_id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id')
        )


def downgrade() -> None:
    """Downgrade schema."""
    # Only drop table if it exists
    conn = op.get_bind()
    inspector = inspect(conn)
    tables = inspector.get_table_names()
    
    if 'weekly_report' in tables:
        op.drop_table('weekly_report')
