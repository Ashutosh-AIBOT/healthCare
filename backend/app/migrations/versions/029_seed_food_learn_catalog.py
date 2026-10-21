"""Seed the initial sourced food catalog used by Learn and Xomni retrieval."""

from typing import Sequence, Union
import json

import sqlalchemy as sa
from alembic import op


revision: str = "029_seed_food_learn_catalog"
down_revision: Union[str, None] = "028_learn_sources"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


SOURCE = {
    "name": "USDA FoodData Central and ICMR-NIN reference guidance",
    "url": "https://fdc.nal.usda.gov/",
    "license": "Public reference data; verify current source terms",
    "version": "starter-catalog-2026-09",
    "content_hash": "aarogya-food-starter-2026-09",
}

CATEGORIES = [
    ("protein-foods", "Protein foods", "food", "Practical protein options with approximate nutrition per serving.", "utensils", 10),
    ("grains-legumes", "Grains and legumes", "food", "Fiber-rich staples for balanced meals and steady energy.", "wheat", 20),
    ("fruit-vegetables", "Fruits and vegetables", "food", "Everyday produce choices, portions, and meal-planning roles.", "leaf", 30),
]

ITEMS = [
    ("paneer-100g", "Paneer (100 g)", "A protein-rich dairy option commonly used in Indian meals.", {"calories": 265, "protein_g": 18, "carbs_g": 6, "fat_g": 20, "serving": "100 g"}, ["protein", "calcium"], "Useful in balanced meals; choose portions that fit the user's energy and saturated-fat needs.", "protein-foods", 10),
    ("lentils-cooked-100g", "Cooked lentils (100 g)", "A plant protein and fiber source for dals, soups, and bowls.", {"calories": 116, "protein_g": 9, "carbs_g": 20, "fat_g": 0.4, "serving": "100 g cooked"}, ["protein", "fiber", "folate"], "Pairs well with vegetables and whole grains for a filling meal.", "protein-foods", 20),
    ("quinoa-cooked-150g", "Cooked quinoa (150 g)", "A versatile grain-like seed that contributes protein and fiber.", {"calories": 166, "protein_g": 6, "carbs_g": 30, "fat_g": 2.5, "serving": "150 g cooked"}, ["fiber", "magnesium"], "Use as one carbohydrate component rather than assuming it is a complete meal by itself.", "grains-legumes", 10),
    ("chickpeas-cooked-100g", "Cooked chickpeas (100 g)", "A filling legume for chana, salads, and mixed bowls.", {"calories": 164, "protein_g": 9, "carbs_g": 27, "fat_g": 2.6, "serving": "100 g cooked"}, ["fiber", "protein", "iron"], "Increase portions gradually if legumes cause digestive discomfort and keep hydration adequate.", "grains-legumes", 20),
    ("banana-medium", "Banana (1 medium)", "A convenient carbohydrate and potassium-containing fruit.", {"calories": 105, "protein_g": 1.3, "carbs_g": 27, "fat_g": 0.4, "serving": "1 medium"}, ["potassium", "carbohydrate"], "Useful around activity for quick fuel; pair with protein when building a more complete snack.", "fruit-vegetables", 10),
    ("spinach-cooked-100g", "Cooked spinach (100 g)", "A leafy vegetable that adds volume and micronutrients to meals.", {"calories": 23, "protein_g": 3, "carbs_g": 3.8, "fat_g": 0.3, "serving": "100 g cooked"}, ["folate", "vitamin K", "fiber"], "Include varied vegetables across the week; people with specific medical conditions should follow clinician guidance.", "fruit-vegetables", 20),
]


def upgrade() -> None:
    bind = op.get_bind()
    bind.execute(
        sa.text(
            """
            INSERT INTO learn_sources (name, url, license, version, retrieved_at, content_hash)
            VALUES (:name, :url, :license, :version, now(), :content_hash)
            ON CONFLICT (content_hash) DO UPDATE SET
              name = EXCLUDED.name, url = EXCLUDED.url, version = EXCLUDED.version,
              retrieved_at = EXCLUDED.retrieved_at
            """
        ),
        SOURCE,
    )
    for slug, title, kind, description, icon, sort_order in CATEGORIES:
        bind.execute(
            sa.text(
                """
                INSERT INTO learn_categories (slug, title, kind, description, icon, sort_order)
                VALUES (:slug, :title, :kind, :description, :icon, :sort_order)
                ON CONFLICT (slug) DO UPDATE SET
                  title = EXCLUDED.title, kind = EXCLUDED.kind, description = EXCLUDED.description,
                  icon = EXCLUDED.icon, sort_order = EXCLUDED.sort_order
                """
            ),
            {"slug": slug, "title": title, "kind": kind, "description": description, "icon": icon, "sort_order": sort_order},
        )
    for slug, title, summary, nutrition, benefits, healthy_role, category_slug, sort_order in ITEMS:
        bind.execute(
            sa.text(
                """
                INSERT INTO learn_items (category_id, slug, title, summary, nutrition, benefits, healthy_role, source_id, sort_order)
                SELECT c.id, :slug, :title, :summary, CAST(:nutrition AS jsonb), CAST(:benefits AS jsonb),
                       :healthy_role, s.id, :sort_order
                FROM learn_categories c
                CROSS JOIN learn_sources s
                WHERE c.slug = :category_slug AND s.content_hash = :content_hash
                ON CONFLICT (slug) DO UPDATE SET
                  category_id = EXCLUDED.category_id, title = EXCLUDED.title, summary = EXCLUDED.summary,
                  nutrition = EXCLUDED.nutrition, benefits = EXCLUDED.benefits,
                  healthy_role = EXCLUDED.healthy_role, source_id = EXCLUDED.source_id, sort_order = EXCLUDED.sort_order
                """
            ),
            {
                "slug": slug,
                "title": title,
                "summary": summary,
                "nutrition": json.dumps(nutrition),
                "benefits": json.dumps(benefits),
                "healthy_role": healthy_role,
                "category_slug": category_slug,
                "sort_order": sort_order,
                "content_hash": SOURCE["content_hash"],
            },
        )


def downgrade() -> None:
    bind = op.get_bind()
    for item in ITEMS:
        bind.execute(sa.text("DELETE FROM learn_items WHERE slug = :slug"), {"slug": item[0]})
    for category in CATEGORIES:
        bind.execute(sa.text("DELETE FROM learn_categories WHERE slug = :slug"), {"slug": category[0]})
    bind.execute(sa.text("DELETE FROM learn_sources WHERE content_hash = :content_hash"), SOURCE)
