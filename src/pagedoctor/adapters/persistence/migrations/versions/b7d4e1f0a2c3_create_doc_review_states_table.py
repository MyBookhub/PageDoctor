"""create doc_review_states table

Revision ID: b7d4e1f0a2c3
Revises: af4a1be91c55
Create Date: 2026-06-26 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "b7d4e1f0a2c3"
down_revision: str | None = "af4a1be91c55"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "doc_review_states",
        sa.Column("doc_id", sa.String(), nullable=False),
        sa.Column("revision_id", sa.String(), nullable=True),
        sa.Column("chunk_hashes", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("config", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("doc_id"),
    )


def downgrade() -> None:
    op.drop_table("doc_review_states")
