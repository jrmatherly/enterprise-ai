#!/usr/bin/env bash
# Validate that .env.example files exist and are well-formed
# .env files are gitignored and not checked here
set -e

ERRORS=0

check_env_example() {
    local example_file="$1"
    local name="$2"
    
    echo "Checking $name..."
    
    # Check .env.example exists
    if [[ ! -f "$example_file" ]]; then
        echo "❌ $name: $example_file not found"
        ERRORS=$((ERRORS + 1))
        return
    fi
    
    # Count variables in .env.example (non-comment, non-empty lines with =)
    VAR_COUNT=$(grep -v "^#" "$example_file" | grep -v "^$" | grep "=" | wc -l | tr -d ' ')
    
    if [[ "$VAR_COUNT" -eq 0 ]]; then
        echo "❌ $name: $example_file has no variables defined"
        ERRORS=$((ERRORS + 1))
        return
    fi
    
    echo "✅ $name: $VAR_COUNT variables in $example_file"
}

# Check backend .env.example
check_env_example "dev/.env.example" "Backend"

# Check frontend .env.example  
check_env_example "frontend/.env.example" "Frontend"

echo ""
if [[ $ERRORS -gt 0 ]]; then
    echo "❌ $ERRORS error(s) found"
    exit 1
fi
echo "✅ All .env.example files validated!"
