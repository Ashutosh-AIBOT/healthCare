"""create family_members table

Revision ID: 007
Revises: 006
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "007"
down_revision: Union[str, None] = "006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    family_members = op.create_table(
        "family_members",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("family_id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", sa.UUID(as_uuid=True), nullable=True),
        sa.Column("relation", sa.String(length=32), nullable=True),
        sa.Column("date_of_birth", sa.Date(), nullable=True),
        sa.Column("gender", sa.String(length=32), nullable=True),
        sa.Column("blood_group", sa.String(length=32), nullable=True),
        sa.Column("is_dependent", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("guardian_id", sa.UUID(as_uuid=True), nullable=True),
        sa.Column("timezone", sa.String(length=64), server_default="Asia/Kolkata", nullable=False),
        sa.Column("diet_preference", sa.String(length=32), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["family_id"], ["families.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["guardian_id"], ["family_members.id"], ondelete="SET NULL"),
    )
    op.create_index(op.f("ix_family_members_family_id"), "family_members", ["family_id"], unique=False)
    op.create_index(op.f("ix_family_members_user_id"), "family_members", ["user_id"], unique=False)
    op.create_index(op.f("ix_family_members_guardian_id"), "family_members", ["guardian_id"], unique=False)
    op.create_check_constraint("ck_family_members_relation", "family_members", "relation IN ('father', 'mother', 'spouse', 'son', 'daughter', 'brother', 'sister', 'grandfather', 'grandmother', 'other') OR relation IS NULL")
    op.create_check_constraint("ck_family_members_gender", "family_members", "gender IN ('male', 'female', 'other', 'prefer_not_to_say') OR gender IS NULL")
    op.create_check_constraint("ck_family_members_blood_group", "family_members", "blood_group IN ('a_pos', 'a_neg', 'b_pos', 'b_neg', 'ab_pos', 'ab_neg', 'o_pos', 'o_neg', 'unknown') OR blood_group IS NULL")
    op.create_check_constraint("ck_family_members_diet_preference", "family_members", "diet_preference IN ('vegetarian', 'non_vegetarian', 'eggetarian', 'vegan', 'jain') OR diet_preference IS NULL")


def downgrade() -> None:
    op.drop_constraint("ck_family_members_diet_preference", "family_members", type_="check")
    op.drop_constraint("ck_family_members_blood_group", "family_members", type_="check")
    op.drop_constraint("ck_family_members_gender", "family_members", type_="check")
    op.drop_constraint("ck_family_members_relation", "family_members", type_="check")
    op.drop_index(op.f("ix_family_members_guardian_id"), table_name="family_members")
    op.drop_index(op.f("ix_family_members_user_id"), table_name="family_members")
    op.drop_index(op.f("ix_family_members_family_id"), table_name="family_members")
    op.drop_table("family_members")
