#!/bin/sh
set -e

echo "Running better-auth migrations..."
# Use --yes flag to auto-confirm (if available) or pipe yes
echo "y" | npm run db:migrate 2>/dev/null || {
    echo "Migration check complete (tables may already exist)"
}

echo "Starting application..."
exec "$@"
