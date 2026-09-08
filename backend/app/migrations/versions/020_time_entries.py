"""add time_entries for activity logging

Revision ID: 020_time_entries
Revises: 019
Create Date: 2026-09-07 17:20:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '020_time_entries'
down_revision: Union[str, None] = '019'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'time_entries',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('family_id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('block_id', sa.UUID(), nullable=False),
        sa.Column('actual_title', sa.String(length=200), nullable=False),
        sa.Column('matched', sa.Boolean(), nullable=False),
        sa.Column('duration_minutes', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['block_id'], ['time_blocks.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['family_id'], ['families.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_time_entries_family_id', 'time_entries', ['family_id'], unique=False)
    op.create_index('ix_time_entries_user_id', 'time_entries', ['user_id'], unique=False)
    op.create_index('ix_time_entries_date', 'time_entries', ['date'], unique=False)
    op.create_index('ix_time_entries_block_id', 'time_entries', ['block_id'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_time_entries_block_id', table_name='time_entries')
    op.drop_index('ix_time_entries_date', table_name='time_entries')
    op.drop_index('ix_time_entries_user_id', table_name='time_entries')
    op.drop_index('ix_time_entries_family_id', table_name='time_entries')
    op.drop_table('time_entries')
