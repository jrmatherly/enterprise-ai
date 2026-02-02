#!/usr/bin/env bash
# Check that .env and .env.example files have the same variables
set -e

echo "Checking backend env files..."
grep -v "^#" dev/.env | grep -v "^$" | cut -d'=' -f1 | sort > /tmp/env_vars
grep -v "^#" dev/.env.example | grep -v "^$" | cut -d'=' -f1 | sort > /tmp/env_example_vars

if ! diff /tmp/env_vars /tmp/env_example_vars > /tmp/env_diff 2>&1; then
    echo "❌ Backend env files have different variables:"
    cat /tmp/env_diff
    exit 1
fi
BACKEND_COUNT=$(wc -l < /tmp/env_vars | tr -d ' ')
echo "✅ Backend: $BACKEND_COUNT variables match"

echo "Checking frontend env files..."
grep -v "^#" frontend/.env.local | grep -v "^$" | cut -d'=' -f1 | sort > /tmp/fe_env_vars
grep -v "^#" frontend/.env.example | grep -v "^$" | cut -d'=' -f1 | sort > /tmp/fe_env_example_vars

if ! diff /tmp/fe_env_vars /tmp/fe_env_example_vars > /tmp/fe_env_diff 2>&1; then
    echo "❌ Frontend env files have different variables:"
    cat /tmp/fe_env_diff
    exit 1
fi
FRONTEND_COUNT=$(wc -l < /tmp/fe_env_vars | tr -d ' ')
echo "✅ Frontend: $FRONTEND_COUNT variables match"

echo ""
echo "✅ All environment files in sync!"
