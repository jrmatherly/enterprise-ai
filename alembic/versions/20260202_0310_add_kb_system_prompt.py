"""Add system_prompt to knowledge_bases

Revision ID: 20260202_0310
Revises: 20260202_0230
Create Date: 2026-02-02 03:10:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260202_0310"
down_revision: str | None = "20260202_0230"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add system_prompt column to knowledge_bases table."""
    op.add_column(
        "knowledge_bases",
        sa.Column(
            "system_prompt",
            sa.Text(),
            nullable=True,
            comment="Custom instructions for AI when using this knowledge base",
        ),
    )


def downgrade() -> None:
    """Remove system_prompt column from knowledge_bases table."""
    op.drop_column("knowledge_bases", "system_prompt")
