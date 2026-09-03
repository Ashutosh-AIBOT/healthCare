"""create nutrition tables

Revision ID: 021
Revises: 020
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "021"
down_revision: Union[str, None] = "020"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "food_items",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("slug", sa.String(length=160), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("serving_unit", sa.String(length=64), nullable=True),
        sa.Column("calories_kcal", sa.Integer(), nullable=True),
        sa.Column("protein_g", sa.Integer(), nullable=True),
        sa.Column("carbs_g", sa.Integer(), nullable=True),
        sa.Column("fat_g", sa.Integer(), nullable=True),
        sa.Column("fiber_g", sa.Integer(), nullable=True),
        sa.Column("glycemic_index", sa.Integer(), nullable=True),
        sa.Column("is_verified", sa.Integer(), server_default=sa.text("0"), nullable=False),
    )
    op.create_index(op.f("ix_food_items_slug"), "food_items", ["slug"], unique=True)

    op.create_table(
        "food_logs",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("member_id", sa.UUID(as_uuid=True), sa.ForeignKey("family_members.id", ondelete="CASCADE"), nullable=False),
        sa.Column("food_item_id", sa.UUID(as_uuid=True), sa.ForeignKey("food_items.id", ondelete="SET NULL"), nullable=True),
        sa.Column("meal_type", sa.String(length=32), nullable=False),
        sa.Column("logged_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=True),
        sa.Column("unit", sa.String(length=32), nullable=True),
        sa.Column("calories_kcal", sa.Integer(), nullable=True),
        sa.Column("protein_g", sa.Integer(), nullable=True),
        sa.Column("carbs_g", sa.Integer(), nullable=True),
        sa.Column("fat_g", sa.Integer(), nullable=True),
        sa.Column("fiber_g", sa.Integer(), nullable=True),
        sa.Column("source", sa.String(length=32), nullable=True),
        sa.Column("image_url", sa.String(length=255), nullable=True),
        sa.Column("is_estimate", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
    )
    op.create_index(op.f("ix_food_logs_member_id"), "food_logs", ["member_id"])

    op.create_table(
        "nutrition_targets",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("member_id", sa.UUID(as_uuid=True), sa.ForeignKey("family_members.id", ondelete="CASCADE"), nullable=False),
        sa.Column("daily_calories_kcal", sa.Integer(), nullable=True),
        sa.Column("daily_protein_g", sa.Integer(), nullable=True),
        sa.Column("daily_carbs_g", sa.Integer(), nullable=True),
        sa.Column("daily_fat_g", sa.Integer(), nullable=True),
        sa.Column("daily_fiber_g", sa.Integer(), nullable=True),
        sa.Column("max_glycemic_index", sa.Integer(), nullable=True),
    )
    op.create_index(op.f("ix_nutrition_targets_member_id"), "nutrition_targets", ["member_id"], unique=True)

    op.create_table(
        "nutrition_plans",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("member_id", sa.UUID(as_uuid=True), sa.ForeignKey("family_members.id", ondelete="CASCADE"), nullable=False),
        sa.Column("start_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=True),
        sa.Column("citations", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Integer(), server_default=sa.text("1"), nullable=False),
    )
    op.create_index(op.f("ix_nutrition_plans_member_id"), "nutrition_plans", ["member_id"])

    conn = op.get_bind()
    conn.execute(sa.text("ALTER TABLE food_items ENABLE ROW LEVEL SECURITY"))
    conn.execute(sa.text("ALTER TABLE food_items FORCE ROW LEVEL SECURITY"))
    conn.execute(sa.text("CREATE POLICY food_items_read ON food_items FOR SELECT USING (is_active = 1 OR current_setting('app.bypass_rls', true) = 'on')"))

    conn.execute(sa.text("ALTER TABLE food_logs ENABLE ROW LEVEL SECURITY"))
    conn.execute(sa.text("ALTER TABLE food_logs FORCE ROW LEVEL SECURITY"))
    conn.execute(
        sa.text(
            """
            CREATE POLICY food_logs_isolation ON food_logs FOR ALL
            USING (
                current_setting('app.bypass_rls', true) = 'on'
                OR EXISTS (
                    SELECT 1 FROM family_members fm
                    WHERE fm.id = food_logs.member_id
                      AND fm.family_id = COALESCE(
                          NULLIF(current_setting('app.family_id', true), '')::uuid,
                          '00000000-0000-0000-0000-000000000000'
                      )
                )
            )
            """
        )
    )

    conn.execute(sa.text("ALTER TABLE nutrition_targets ENABLE ROW LEVEL SECURITY"))
    conn.execute(sa.text("ALTER TABLE nutrition_targets FORCE ROW LEVEL SECURITY"))
    conn.execute(
        sa.text(
            """
            CREATE POLICY nutrition_targets_isolation ON nutrition_targets FOR ALL
            USING (
                current_setting('app.bypass_rls', true) = 'on'
                OR EXISTS (
                    SELECT 1 FROM family_members fm
                    WHERE fm.id = nutrition_targets.member_id
                      AND fm.family_id = COALESCE(
                          NULLIF(current_setting('app.family_id', true), '')::uuid,
                          '00000000-0000-0000-0000-000000000000'
                      )
                )
            )
            """
        )
    )

    conn.execute(sa.text("ALTER TABLE nutrition_plans ENABLE ROW LEVEL SECURITY"))
    conn.execute(sa.text("ALTER TABLE nutrition_plans FORCE ROW LEVEL SECURITY"))
    conn.execute(
        sa.text(
            """
            CREATE POLICY nutrition_plans_isolation ON nutrition_plans FOR ALL
            USING (
                current_setting('app.bypass_rls', true) = 'on'
                OR EXISTS (
                    SELECT 1 FROM family_members fm
                    WHERE fm.id = nutrition_plans.member_id
                      AND fm.family_id = COALESCE(
                          NULLIF(current_setting('app.family_id', true), '')::uuid,
                          '00000000-0000-0000-0000-000000000000'
                      )
                )
            )
            """
        )
    )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text("DROP POLICY IF EXISTS nutrition_plans_isolation ON nutrition_plans"))
    conn.execute(sa.text("ALTER TABLE nutrition_plans DISABLE ROW LEVEL SECURITY"))
    conn.execute(sa.text("DROP POLICY IF EXISTS nutrition_targets_isolation ON nutrition_targets"))
    conn.execute(sa.text("ALTER TABLE nutrition_targets DISABLE ROW LEVEL SECURITY"))
    conn.execute(sa.text("DROP POLICY IF EXISTS food_logs_isolation ON food_logs"))
    conn.execute(sa.text("ALTER TABLE food_logs DISABLE ROW LEVEL SECURITY"))
    conn.execute(sa.text("DROP POLICY IF EXISTS food_items_read ON food_items"))
    conn.execute(sa.text("ALTER TABLE food_items DISABLE ROW LEVEL SECURITY"))
    op.drop_index(op.f("ix_nutrition_plans_member_id"), table_name="nutrition_plans")
    op.drop_table("nutrition_plans")
    op.drop_index(op.f("ix_nutrition_targets_member_id"), table_name="nutrition_targets")
    op.drop_table("nutrition_targets")
    op.drop_index(op.f("ix_food_logs_member_id"), table_name="food_logs")
    op.drop_table("food_logs")
    op.drop_index(op.f("ix_food_items_slug"), table_name="food_items")
    op.drop_table("food_items")
