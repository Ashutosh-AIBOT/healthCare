"""add learn embeddings and content fields

Revision ID: 021_learn_embeddings
Revises: 020_time_entries
Create Date: 2026-09-07 18:45:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = '021_learn_embeddings'
down_revision: Union[str, None] = '020_time_entries'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('learn_items', sa.Column('content', sa.Text(), nullable=True))
    op.add_column('learn_items', sa.Column('image_url', sa.String(length=255), nullable=True))
    op.add_column('learn_items', sa.Column('embedding', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('body_tests', sa.Column('embedding', postgresql.JSONB(astext_type=sa.Text()), nullable=True))


def downgrade() -> None:
    op.drop_column('body_tests', 'embedding')
    op.drop_column('learn_items', 'embedding')
    op.drop_column('learn_items', 'image_url')
    op.drop_column('learn_items', 'content')
