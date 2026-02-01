# Development Environment Setup

**Last Updated:** 2026-02-01

This guide walks you through setting up the local development environment. **Everything runs in Docker** with hot reload enabled for rapid development.

## Prerequisites

- [mise](https://mise.jdx.dev/getting-started.html) - Task runner
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (or Docker Engine + Compose)
- Azure AI Foundry access (for LLM inference)

### Installing mise (if not already installed)

```bash
# macOS (Homebrew)
brew install mise

# Or using the installer
curl https://mise.run | sh

# Add to shell (bash/zsh)
echo 'eval "$(mise activate zsh)"' >> ~/.zshrc
source ~/.zshrc
```

## Quick Start

```bash
# Navigate to project root
cd projects/enterprise-ai-platform

# First-time setup (builds containers, starts everything, runs migrations)
mise run setup

# Or if already set up, just start:
mise run dev
```

That's it! Everything is now running in Docker with hot reload enabled:

| Service | URL | Description |
|---------|-----|-------------|
| **Frontend** | http://localhost:3001 | Next.js chat UI |
| **Backend API** | http://localhost:8000 | FastAPI |
| **API Docs** | http://localhost:8000/docs | Swagger UI |
| **Langfuse** | http://localhost:3000 | LLM observability |

## Hot Reload

Both the backend and frontend have hot reload enabled:

- **Backend (Python)**: Edit files in `src/` — uvicorn auto-reloads
- **Frontend (Next.js)**: Edit files in `frontend/src/` — Next.js auto-reloads

No need to rebuild containers for code changes!

## Testing the API

```bash
# Quick test (uses dev bypass auth)
mise run chat

# Or manually:
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -H "X-Dev-Bypass: true" \
  -d '{"message": "Hello! What can you help me with?"}'
```

## Common Tasks

```bash
# View all logs
mise run logs

# View only backend/frontend logs
mise run logs-app

# Rebuild containers after dependency changes
mise run rebuild

# Stop everything
mise run stop

# Full reset (deletes all data!)
mise run reset

# Open shell in containers
mise run backend-shell
mise run ui-shell
```

## Database Tasks

```bash
# Apply pending migrations
mise run db-upgrade

# Generate new migration (after changing models)
mise run db-migrate "description of changes"

# Rollback one migration
mise run db-downgrade

# Seed development data
mise run seed
```

## Alternative: Local Development Workflow

If you prefer running backend/frontend locally (faster iteration, easier debugging):

```bash
# Start only infrastructure in Docker
mise run dev-local

# Then in separate terminals:
uv run uvicorn src.api.main:app --reload --port 8000
cd frontend && npm run dev
```

This requires Python 3.12 and Node.js installed locally via mise:

```bash
# First-time local setup
mise install              # Install Python/Node
uv sync --all-extras      # Python deps
cd frontend && npm install  # Node deps
```

## Project Structure

```
enterprise-ai-platform/
├── mise.toml            # Task definitions
├── pyproject.toml       # Python dependencies
├── uv.lock              # Python lockfile
├── frontend/            # Next.js application
│   ├── src/
│   │   ├── app/         # Next.js pages
│   │   ├── components/  # React components
│   │   └── lib/         # API client, hooks
│   └── package.json
├── src/                 # FastAPI backend
│   ├── api/             # Routes and middleware
│   ├── agent/           # Azure AI integration
│   ├── auth/            # Authentication
│   ├── core/            # Config, rate limiting
│   ├── db/              # Database models
│   └── rag/             # RAG pipeline
├── alembic/             # Database migrations
├── dev/                 # Development stack
│   ├── docker-compose.yml
│   ├── Dockerfile.backend
│   ├── Dockerfile.frontend
│   ├── .env             # Environment variables
│   └── init-scripts/    # Database init
└── docs/                # Documentation
```

## Docker Services

| Service | Port(s) | Description |
|---------|---------|-------------|
| **backend** | 8000 | FastAPI application |
| **frontend** | 3001 | Next.js application |
| **postgres** | 5432 | PostgreSQL 17 |
| **redis** | 6379 | Redis 7 |
| **qdrant** | 6333, 6334 | Vector database |
| **langfuse-web** | 3000 | Langfuse UI |
| **langfuse-worker** | 3030 | Langfuse processor |
| **clickhouse** | 8123, 9000 | OLAP database |
| **minio** | 9090, 9091 | S3-compatible storage |

## Database Architecture

Two PostgreSQL databases in the same instance:

| Database | Purpose | Managed By |
|----------|---------|------------|
| `langfuse` | Observability data | Prisma (Langfuse) |
| `eai` | Application data | Alembic (us) |

## Environment Configuration

Edit `dev/.env` to configure:

- **PostgreSQL** credentials
- **Azure AI Foundry** endpoints and keys
- **Entra ID** tenant and client IDs
- **Langfuse** initialization settings

### Generate Secure Secrets

```bash
# Passwords (alphanumeric)
openssl rand -base64 24 | tr -d '/+=' | head -c 32

# NEXTAUTH_SECRET
openssl rand -base64 32

# ENCRYPTION_KEY (64 hex chars)
openssl rand -hex 32
```

## Authentication in Development

The auth middleware supports dev bypass mode:

```bash
# Add this header to skip auth
curl -H "X-Dev-Bypass: true" http://localhost:8000/api/v1/chat ...
```

## Troubleshooting

### Container won't start

```bash
# Check logs
mise run logs

# Rebuild from scratch
mise run reset
```

### Database migration fails

```bash
mise run db-current   # Check current state
mise run db-history   # View history
mise run db-reset     # Nuclear option
```

### Hot reload not working

Check that volumes are mounted correctly:

```bash
docker compose -f dev/docker-compose.yml config
```

### Port already in use

```bash
lsof -i :8000    # Find process
kill <PID>       # Kill it
```

## All mise Tasks

```bash
mise tasks       # List all available tasks
```

Key tasks:

| Task | Description |
|------|-------------|
| `setup` | First-time setup (build, start, migrate) |
| `dev` | Start all services |
| `dev-local` | Start infra only (run app locally) |
| `stop` | Stop all services |
| `logs` | Follow all logs |
| `logs-app` | Follow backend/frontend logs |
| `rebuild` | Rebuild backend/frontend containers |
| `reset` | Full reset (deletes data!) |
| `db-upgrade` | Apply migrations |
| `db-migrate` | Generate migration |
| `seed` | Seed dev data |
| `chat` | Quick chat test |
| `backend-shell` | Shell in backend container |
| `ui-shell` | Shell in frontend container |

## References

- [mise documentation](https://mise.jdx.dev/)
- [Docker Compose](https://docs.docker.com/compose/)
- [FastAPI](https://fastapi.tiangolo.com/)
- [Next.js](https://nextjs.org/docs)
- [Langfuse self-hosting](https://langfuse.com/self-hosting)
