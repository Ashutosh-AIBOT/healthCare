"""add search fields to provider_profiles and provider_services

Revision ID: 014
Revises: 013
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision: str = "014"
down_revision: Union[str, None] = "013"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("provider_profiles", sa.Column("city", sa.String(120), nullable=True))
    op.add_column("provider_profiles", sa.Column("state", sa.String(120), nullable=True))
    op.add_column("provider_profiles", sa.Column("country", sa.String(120), server_default="India", nullable=False))
    op.add_column("provider_profiles", sa.Column("pincode", sa.String(10), nullable=True))
    op.add_column("provider_profiles", sa.Column("rating", sa.Float(), nullable=True))
    op.add_column("provider_profiles", sa.Column("response_rate", sa.Float(), nullable=True))
    op.add_column("provider_profiles", sa.Column("completion_rate", sa.Float(), nullable=True))
    op.create_index("ix_provider_profiles_city", "provider_profiles", ["city"])
    op.create_index("ix_provider_profiles_state", "provider_profiles", ["state"])
    op.create_index("ix_provider_profiles_pincode", "provider_profiles", ["pincode"])


def downgrade() -> None:
    op.drop_index("ix_provider_profiles_pincode", table_name="provider_profiles")
    op.drop_index("ix_provider_profiles_state", table_name="provider_profiles")
    op.drop_index("ix_provider_profiles_city", table_name="provider_profiles")
    op.drop_column("provider_profiles", "completion_rate")
    op.drop_column("provider_profiles", "response_rate")
    op.drop_column("provider_profiles", "rating")
    op.drop_column("provider_profiles", "pincode")
    op.drop_column("provider_profiles", "country")
    op.drop_column("provider_profiles", "state")
    op.drop_column("provider_profiles", "city")
