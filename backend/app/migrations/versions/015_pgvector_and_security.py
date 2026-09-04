"""pgvector + security hardening (embedding model, revocation stub)

Revision ID: 015
Revises: 014
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "015"
down_revision: Union[str, None] = "014"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # pgvector extension (requires image pgvector/pgvector:pg16 — already in docker-compose)
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # document_chunks: prepare for pgvector HNSW (keep JSONB embedding during migration, add sidecar columns)
    op.add_column("document_chunks", sa.Column("embedding_model", sa.String(64), nullable=True))
    op.add_column("document_chunks", sa.Column("source", sa.String(120), nullable=True, server_default="lab_report"))
    op.add_column("document_chunks", sa.Column("last_reviewed_at", sa.DateTime(timezone=True), nullable=True))
    # Optional: add VECTOR column when ready (commented — switch JSONB→VECTOR in follow-up to avoid downtime)
    # op.execute("ALTER TABLE document_chunks ADD COLUMN embedding_vec vector(1536)")

    # Index for chunk review job
    op.create_index("ix_document_chunks_last_reviewed_at", "document_chunks", ["last_reviewed_at"])

    # Helpful composite for RAG retrieval pre-filter (family + member)
    op.create_index("ix_document_chunks_family_member", "document_chunks", ["family_id", "member_id"])


def downgrade() -> None:
    op.drop_index("ix_document_chunks_family_member", table_name="document_chunks")
    op.drop_index("ix_document_chunks_last_reviewed_at", table_name="document_chunks")
    op.drop_column("document_chunks", "last_reviewed_at")
    op.drop_column("document_chunks", "source")
    op.drop_column("document_chunks", "embedding_model")
    op.execute("DROP EXTENSION IF EXISTS vector")
