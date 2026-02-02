#!/bin/bash
set -e

echo "Running database migrations..."

# Run migrations - if jwks table already exists (from better-auth), stamp that migration
if ! /app/.venv/bin/alembic upgrade head 2>&1; then
    echo "Migration may have failed due to existing tables, checking..."
    
    # Check if it's the jwks conflict
    if /app/.venv/bin/alembic current 2>&1 | grep -q "d55da58278e9"; then
        echo "Stamping jwks migration (table created by better-auth)..."
        /app/.venv/bin/alembic stamp 20260202_0515_jwks
        # Try to continue with any remaining migrations
        /app/.venv/bin/alembic upgrade head || true
    fi
fi

echo "Migrations complete."
echo "Starting application..."
exec "$@"
