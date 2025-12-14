"""create_weekly_steps_table

Revision ID: 0665aaf05f2a
Revises: f3a96b659211
Create Date: 2025-12-14 03:35:23.922232

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = '0665aaf05f2a'
down_revision: Union[str, Sequence[str], None] = 'f3a96b659211'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Check if weekly_steps table exists, create if not
    conn = op.get_bind()
    inspector = inspect(conn)
    tables = inspector.get_table_names()
    
    if 'weekly_steps' not in tables:
        op.create_table(
            'weekly_steps',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('week', sa.String(length=10), nullable=False),
            sa.Column('steps', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('created_at', sa.TIMESTAMP(), nullable=True),
            sa.Column('updated_at', sa.TIMESTAMP(), nullable=True),
            sa.ForeignKeyConstraint(['user_id'], ['users.user_id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('user_id', 'week', name='unique_user_week')
        )


def downgrade() -> None:
    """Downgrade schema."""
    # Only drop table if it exists
    conn = op.get_bind()
    inspector = inspect(conn)
    tables = inspector.get_table_names()
    
    if 'weekly_steps' in tables:
        op.drop_table('weekly_steps')
