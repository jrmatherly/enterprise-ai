"""add grounded_only to knowledge bases

Revision ID: acd073136bee
Revises: 20260202_0310
Create Date: 2026-02-02 15:40:38.911964+00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "acd073136bee"
down_revision: str | None = "20260202_0310"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "knowledge_bases",
        sa.Column(
            "grounded_only",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
            comment="When true, AI must only respond using KB contents, no external knowledge",
        ),
    )


def downgrade() -> None:
    op.drop_column("knowledge_bases", "grounded_only")
