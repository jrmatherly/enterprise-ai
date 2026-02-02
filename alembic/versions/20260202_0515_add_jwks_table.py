"""Add jwks table for better-auth JWT plugin.

Revision ID: 20260202_0515_jwks
Revises: d55da58278e9
Create Date: 2026-02-02 05:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260202_0515_jwks"
down_revision: Union[str, None] = "d55da58278e9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create jwks table for better-auth JWT plugin."""
    op.create_table(
        "jwks",
        sa.Column("id", sa.String(length=255), nullable=False),
        sa.Column("publicKey", sa.Text(), nullable=False),
        sa.Column("privateKey", sa.Text(), nullable=False),
        sa.Column("createdAt", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expiresAt", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    """Drop jwks table."""
    op.drop_table("jwks")
