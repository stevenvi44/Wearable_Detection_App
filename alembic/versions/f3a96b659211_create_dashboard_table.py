"""create_dashboard_table

Revision ID: f3a96b659211
Revises: 4bb800eb2d40
Create Date: 2025-12-14 03:16:01.140055

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = 'f3a96b659211'
down_revision: Union[str, Sequence[str], None] = '4bb800eb2d40'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Check if dashboard table exists, create if not
    conn = op.get_bind()
    inspector = inspect(conn)
    tables = inspector.get_table_names()
    
    if 'dashboard' not in tables:
        op.create_table(
            'dashboard',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=True),
            sa.Column('date', sa.Date(), nullable=False),
            sa.Column('daily_steps', sa.Integer(), nullable=True, server_default='0'),
            sa.Column('active_minutes', sa.Integer(), nullable=True, server_default='0'),
            sa.Column('rest_hours', sa.Float(), nullable=True, server_default='0.0'),
            sa.Column('mobility_level', sa.String(length=20), nullable=False),
            sa.Column('created_at', sa.TIMESTAMP(), nullable=True),
            sa.ForeignKeyConstraint(['user_id'], ['users.user_id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('user_id', 'date', name='unique_user_date')
        )


def downgrade() -> None:
    """Downgrade schema."""
    # Only drop table if it exists
    conn = op.get_bind()
    inspector = inspect(conn)
    tables = inspector.get_table_names()
    
    if 'dashboard' in tables:
        op.drop_table('dashboard')
