"""create member_transfers table

Revision ID: 010
Revises: 009
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "010"
down_revision: Union[str, None] = "009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "member_transfers",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("member_id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("from_family_id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("to_family_id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="pending", nullable=False),
        sa.Column("requested_by_user_id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("confirmed_by_user_id", sa.UUID(as_uuid=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["member_id"], ["family_members.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["from_family_id"], ["families.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["to_family_id"], ["families.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["requested_by_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["confirmed_by_user_id"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index(op.f("ix_member_transfers_member_id"), "member_transfers", ["member_id"], unique=False)
    op.create_check_constraint("ck_member_transfers_status", "member_transfers", "status IN ('pending', 'approved', 'rejected', 'completed')")


def downgrade() -> None:
    op.drop_constraint("ck_member_transfers_status", "member_transfers", type_="check")
    op.drop_index(op.f("ix_member_transfers_member_id"), table_name="member_transfers")
    op.drop_table("member_transfers")
