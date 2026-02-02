"""Change user_id columns from UUID to VARCHAR for better-auth compatibility.

better-auth uses 32-character string IDs (like FXRoqSj9jXywAbAPmayiGk4DTkb95XlM),
not UUIDs. This migration changes user_id columns to VARCHAR(255).

Revision ID: 20260202_0230_varchar
Revises: 20260202_0515_jwks
Create Date: 2026-02-02 02:30:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260202_0230_varchar"
down_revision: str | None = "20260202_0515_jwks"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Drop foreign key constraints first
    op.drop_constraint("sessions_user_id_fkey", "sessions", type_="foreignkey")
    op.drop_constraint("usage_records_user_id_fkey", "usage_records", type_="foreignkey")
    op.drop_constraint("audit_logs_user_id_fkey", "audit_logs", type_="foreignkey")

    # Change user_id columns from UUID to VARCHAR
    op.alter_column(
        "sessions",
        "user_id",
        existing_type=sa.UUID(as_uuid=False),
        type_=sa.String(255),
        existing_nullable=False,
        postgresql_using="user_id::text",
    )

    op.alter_column(
        "usage_records",
        "user_id",
        existing_type=sa.UUID(as_uuid=False),
        type_=sa.String(255),
        existing_nullable=False,
        postgresql_using="user_id::text",
    )

    op.alter_column(
        "audit_logs",
        "user_id",
        existing_type=sa.UUID(as_uuid=False),
        type_=sa.String(255),
        existing_nullable=True,
        postgresql_using="user_id::text",
    )

    # Change users table id from UUID to VARCHAR
    # First drop the foreign key that references it
    op.alter_column(
        "users",
        "id",
        existing_type=sa.UUID(as_uuid=False),
        type_=sa.String(255),
        existing_nullable=False,
        postgresql_using="id::text",
    )

    # Note: We don't recreate foreign keys since better-auth manages
    # the user table separately and IDs won't match


def downgrade() -> None:
    # Revert changes (this will fail if data doesn't convert to UUID)
    op.alter_column(
        "users",
        "id",
        existing_type=sa.String(255),
        type_=sa.UUID(as_uuid=False),
        existing_nullable=False,
        postgresql_using="id::uuid",
    )

    op.alter_column(
        "audit_logs",
        "user_id",
        existing_type=sa.String(255),
        type_=sa.UUID(as_uuid=False),
        existing_nullable=True,
        postgresql_using="user_id::uuid",
    )

    op.alter_column(
        "usage_records",
        "user_id",
        existing_type=sa.String(255),
        type_=sa.UUID(as_uuid=False),
        existing_nullable=False,
        postgresql_using="user_id::uuid",
    )

    op.alter_column(
        "sessions",
        "user_id",
        existing_type=sa.String(255),
        type_=sa.UUID(as_uuid=False),
        existing_nullable=False,
        postgresql_using="user_id::uuid",
    )

    # Recreate foreign keys
    op.create_foreign_key("audit_logs_user_id_fkey", "audit_logs", "users", ["user_id"], ["id"])
    op.create_foreign_key(
        "usage_records_user_id_fkey", "usage_records", "users", ["user_id"], ["id"]
    )
    op.create_foreign_key("sessions_user_id_fkey", "sessions", "users", ["user_id"], ["id"])
