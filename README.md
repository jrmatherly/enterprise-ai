# Enterprise AI Platform

Enterprise-grade AI adoption platform with RBAC, RAG, and multi-tenant support.

## Features

- **Multi-tenant Architecture**: Organization → Department → Team hierarchy
- **RBAC**: Role-based access control with fine-grained permissions
- **RAG Pipeline**: Document ingestion and retrieval-augmented generation
- **Chat Interface**: Real-time streaming chat with AI assistants
- **Observability**: Full tracing with Langfuse integration
- **Rate Limiting**: TPM/RPM limits per tenant and user

## Tech Stack

- **Backend**: FastAPI, Python 3.12, SQLAlchemy, Alembic
- **Frontend**: Next.js 15, React 19, TypeScript, Tailwind CSS
- **Database**: PostgreSQL 17, Redis 7, Qdrant
- **AI**: Azure AI Foundry, OpenAI
- **Observability**: Langfuse v3, Prometheus

## Quick Start

```bash
# First-time setup
mise run setup

# Start development (all services in Docker with hot reload)
mise run dev
```

## Development Workflow

```bash
# Check for issues before committing
hk check

# Auto-fix issues
hk fix

# Commit (hooks run silently)
git commit -m "feat(scope): description"

# Push
git push origin main
```

Git hooks enforce:
- **Pre-commit**: Linting, formatting, security checks
- **Commit-msg**: [Conventional Commits](https://www.conventionalcommits.org/) format

See [Contributing Guide](docs/CONTRIBUTING.md) for full workflow details.

Services:
- Frontend: http://localhost:3001
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Langfuse: http://localhost:3000

## Documentation

- [Contributing Guide](docs/CONTRIBUTING.md) — Git workflow, commit conventions
- [Development Setup](dev/SETUP.md)
- [Frontend Architecture](docs/FRONTEND-ARCHITECTURE.md)
- [Implementation Plan](IMPLEMENTATION-PLAN.md)
- [Mise Enhancements](docs/MISE-ENHANCEMENT-OPPORTUNITIES.md)

## License

MIT
