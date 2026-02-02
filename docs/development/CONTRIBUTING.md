# Contributing / Development Workflow

## Git Workflow

### First-Time Setup

After cloning the repo, install git hooks:

```bash
mise run git:hooks:install
```

This sets up pre-commit and commit-msg hooks for linting, formatting, and security checks.

### Before You Commit

Always check for issues before committing:

```bash
# Check for linting, formatting, and security issues
hk check

# Or use mise task
mise run git:hooks:check
```

### Fix Issues

Auto-fix what can be fixed:

```bash
# Auto-fix linting and formatting issues
hk fix

# Or use mise task
mise run git:hooks:fix
```

### Commit

Once issues are resolved, commit normally:

```bash
git add .
git commit -m "feat(scope): your message"
```

**Note:** Git hooks run silently (output redirected). If a commit is rejected, run `hk check` to see why.

### Push

Push directly to main (or create a branch for PRs):

```bash
git push origin main
```

---

## Commit Message Format

We use [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

### Types

| Type | Description |

|------|-------------|
| `feat` | New feature |
| `fix` | Bug fix |
| `docs` | Documentation only |
| `style` | Formatting, no code change |
| `refactor` | Code change that neither fixes a bug nor adds a feature |
| `perf` | Performance improvement |
| `test` | Adding or fixing tests |
| `build` | Build system or dependencies |
| `ci` | CI configuration |
| `chore` | Other changes (e.g., tooling) |
| `revert` | Reverts a previous commit |

### Examples

```bash
git commit -m "feat(auth): add Microsoft SSO support"
git commit -m "fix(chat): resolve streaming timeout issue"
git commit -m "docs: update API documentation"
git commit -m "refactor(rag): simplify chunking logic"
```

---

## Quick Reference

```bash
# Full workflow
hk check                    # 1. Check for issues
hk fix                      # 2. Auto-fix issues
git add .                   # 3. Stage changes
git commit -m "type: msg"   # 4. Commit (hooks run silently)
git push origin main        # 5. Push

# Skip hooks (emergency only)
HK=0 git commit -m "emergency fix"

# Run full CI locally
mise run ci
```

---

## Why Silent Hooks?

Git hooks run with output suppressed to prevent AI coding assistants (Claude Code, etc.) from crashing due to hk's verbose streaming output.

**What this means:**
- ✅ Hooks still run and validate
- ✅ Bad commits are still blocked (exit codes work)
- ❌ You won't see hk output during `git commit`
- 💡 Run `hk check` manually to see issues

---

## Troubleshooting

### Commit rejected but no output

Run `hk check` to see what failed:

```bash
hk check
```

### Bypass hooks temporarily

```bash
HK=0 git commit -m "message"
```

### Reinstall hooks

```bash
mise run hooks-install
```

Then manually update hooks for silent mode:

```bash
# Edit .git/hooks/pre-commit and .git/hooks/commit-msg
# Add: > /dev/null 2>&1
```

## Database Migrations

**Always use Alembic to generate migrations:**

```bash
# From dev directory, generate a new migration
docker compose exec backend uv run alembic revision --autogenerate -m "Description of change"

# Or locally with uv
uv run alembic revision --autogenerate -m "Description of change"
```

**Never create migration files manually** - Alembic automatically:
- Sets the correct `down_revision` (parent migration)
- Detects schema changes from SQLAlchemy models
- Handles the revision chain properly

**Migrations run automatically on container startup** via `dev/scripts/backend-entrypoint.sh`.

### Checking Migration Status

```bash
# Current migration version
docker compose exec backend uv run alembic current

# Migration history
docker compose exec backend uv run alembic history

# Pending migrations
docker compose exec backend uv run alembic upgrade head --sql
```
