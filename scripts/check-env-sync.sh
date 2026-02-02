#!/usr/bin/env bash
# Validate that .env.example files exist and are well-formed
# In CI: just validates .env.example files exist and have content
# Locally: can compare .env vs .env.example (if .env exists)
set -e

ERRORS=0

check_env_example() {
    local dir="$1"
    local name="$2"
    local example_file="$dir/.env.example"
    local env_file="$dir/.env"
    
    # Special case for dev directory
    if [[ "$dir" == "dev" ]]; then
        env_file="dev/.env"
        example_file="dev/.env.example"
    fi
    
    # Special case for frontend
    if [[ "$dir" == "frontend" ]]; then
        env_file="frontend/.env.local"
        example_file="frontend/.env.example"
    fi
    
    echo "Checking $name..."
    
    # Check .env.example exists
    if [[ ! -f "$example_file" ]]; then
        echo "❌ $name: $example_file not found"
        ERRORS=$((ERRORS + 1))
        return
    fi
    
    # Count variables in .env.example
    VAR_COUNT=$(grep -v "^#" "$example_file" | grep -v "^$" | grep "=" | wc -l | tr -d ' ')
    
    if [[ "$VAR_COUNT" -eq 0 ]]; then
        echo "❌ $name: $example_file has no variables"
        ERRORS=$((ERRORS + 1))
        return
    fi
    
    # If .env exists locally, compare them
    if [[ -f "$env_file" ]]; then
        grep -v "^#" "$env_file" 2>/dev/null | grep -v "^$" | cut -d'=' -f1 | sort > /tmp/env_vars_$$ || true
        grep -v "^#" "$example_file" | grep -v "^$" | cut -d'=' -f1 | sort > /tmp/env_example_vars_$$
        
        if ! diff /tmp/env_vars_$$ /tmp/env_example_vars_$$ > /tmp/env_diff_$$ 2>&1; then
            echo "⚠️  $name: $env_file and $example_file have different variables (local only)"
            cat /tmp/env_diff_$$
            # Don't fail on this - just warn
        else
            echo "✅ $name: $VAR_COUNT variables (synced with local .env)"
        fi
        
        rm -f /tmp/env_vars_$$ /tmp/env_example_vars_$$ /tmp/env_diff_$$
    else
        echo "✅ $name: $VAR_COUNT variables in .env.example"
    fi
}

# Check backend (dev directory)
check_env_example "dev" "Backend"

# Check frontend
check_env_example "frontend" "Frontend"

echo ""
if [[ $ERRORS -gt 0 ]]; then
    echo "❌ $ERRORS error(s) found"
    exit 1
fi
echo "✅ All .env.example files validated!"
