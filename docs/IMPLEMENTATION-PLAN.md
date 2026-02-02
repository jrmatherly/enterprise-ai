# Implementation Plan — Enterprise AI Platform MVP

**Created:** 2026-01-31
**Last Updated:** 2026-02-02 (Session 2)
**Status:** Phase 2 Complete, Infrastructure Hardened, Phase 3 Ready

---

## Phase Overview

| Phase | Focus | Duration | Status |

|-------|-------|----------|--------|
| **Phase 0** | Setup & Validation | 1 week | ✅ Complete |
| **Phase 1** | Core Foundation | 2 weeks | ✅ Complete |
| **Phase 2** | RAG & Knowledge Bases | 1.5 weeks | ✅ Complete |
| **Infra** | Docs, Tooling, CI/CD | 1 day | ✅ Complete |
| **Phase 3** | Channels (Slack + Web) | 1 week | ⏳ Next |
| **Phase 4** | Admin & Polish | 0.5-1 week | ⏳ Not Started |

---

## Phase 0: Setup & Validation ✅ COMPLETE

**Goal:** Validate core technology choices, set up development environment.

### 0.1 Azure AI Foundry Setup ✅
- [x] Research multi-region deployment patterns
- [x] Document AZURE-AI-FOUNDRY-SETUP.md
- [x] Azure AI Foundry resources created (East US, East US 2)
- [x] Models deployed and accessible
- [x] API endpoints and keys configured in `.env`
- [x] **Validated:** Chat endpoint successfully calls Azure AI (gpt-5-mini responding)

### 0.2 Development Environment ✅
- [x] Create docker-compose.yml (PostgreSQL, Redis, Qdrant, Langfuse v3, MinIO, ClickHouse)
- [x] All services running and healthy
- [x] Database schema created via Alembic migrations
- [x] Langfuse accessible at localhost:3000
- [x] mise tasks configured for development workflow

### 0.3 Technology Validation ✅
All "spikes" from original plan are validated through working implementation:
- [x] **Azure AI Foundry:** Agent runtime connects and receives responses
- [x] **Database:** SQLAlchemy async + Alembic migrations working
- [x] **Auth:** Middleware with dev bypass implemented (EntraID ready)
- [ ] **Qdrant RAG:** Collection setup pending (Phase 2)

---

## Phase 1: Core Foundation 🔄 IN PROGRESS

**Goal:** Build the core API, authentication, and agent runtime.

### 1.1 Project Structure ✅
```
enterprise-ai-platform/
├── src/
│   ├── api/              ✅ FastAPI routes
│   ├── agent/            ✅ Agent runtime (Azure AI)
│   ├── auth/             ✅ Auth middleware + RBAC
│   ├── core/             ✅ Config, utilities, rate limiting
│   ├── db/               ✅ Models, migrations
│   ├── observability/    🔄 Partial
│   └── rag/              ✅ RAG pipeline
├── alembic/              ✅ Migrations
├── dev/                  ✅ Docker stack
├── frontend/             ✅ Next.js chat UI
└── tests/                ⏳ Pending
```

### 1.2 Core API (FastAPI) ✅
- [x] Set up FastAPI project with proper structure
- [x] Implement health check endpoints (`/health/live`, `/health/ready`)
- [x] Prometheus metrics endpoint (`/metrics`)
- [x] OpenAPI docs (`/docs`, `/redoc`)
- [x] CORS middleware configured
- [ ] OpenTelemetry tracing (partial)
- [ ] Structured JSON logging (partial)

### 1.3 Authentication & Authorization ✅
- [x] OIDC token validation middleware (EntraID)
- [x] Extract user claims from JWT
- [x] Dev bypass mode for testing (`X-Dev-Bypass: true`)
- [x] RBAC permission checking (Permission enum, role mappings)
- [x] `@require_permission` decorator and `PermissionChecker` dependency
- [x] Frontend: better-auth with Microsoft EntraID SSO
- [ ] Auth integration tests

### 1.4 Rate Limiting ✅
- [x] Implement `TokenRateLimiter` class (TPM)
- [x] Implement `RequestRateLimiter` class (RPM)
- [x] `CombinedRateLimiter` wrapping both
- [x] Tenant-specific limits from Redis
- [x] 429 response with `Retry-After` and `X-RateLimit-*` headers
- [ ] Add rate limit metrics to Prometheus

### 1.5 Agent Runtime ✅
- [x] Create `AgentRuntime` class for session management
- [x] Integrate Azure OpenAI SDK (multi-region)
- [x] Model routing based on configuration
- [x] Streaming response support (SSE)
- [x] Langfuse integration initialized
- [ ] Conversation history from database
- [ ] Tool registry

### 1.6 Database Layer ✅
- [x] SQLAlchemy models defined:
  - `Tenant` (multi-tier hierarchy)
  - `User` (EntraID identity cache)
  - `Session` (chat sessions)
  - `Message` (conversation history)
  - `KnowledgeBase` (RAG collections)
  - `Document` (document metadata)
  - `AuditLog` (compliance)
  - `UsageRecord` (FinOps)
- [x] Alembic migrations working
- [x] Async database sessions (asyncpg)
- [ ] Message persistence in chat flow ⏳ NEXT
- [ ] Repository pattern helpers

---

## Phase 1 Remaining Work

### Rate Limiting (Priority: High)
Implement token-based rate limiting per tenant:

```python
# Target implementation
class TokenRateLimiter:
    async def check_limit(self, tenant_id: str, tokens: int) -> bool
    async def record_usage(self, tenant_id: str, tokens: int) -> None
```

**Tasks:**
1. Create `src/core/rate_limiting.py` with `TokenRateLimiter`
2. Add middleware to check limits before LLM calls
3. Read limits from tenant configuration in database
4. Return 429 with proper headers when exceeded

### Message Persistence (Priority: High)
Store conversation history in database:

**Tasks:**
1. Add repository methods for Session and Message
2. Update chat route to:
   - Create/retrieve session
   - Store user message before LLM call
   - Store assistant response after LLM call
3. Support conversation continuity via `session_id`

---

## Phase 2: RAG & Knowledge Bases ✅ COMPLETE

**Goal:** Implement document ingestion and retrieval with access control.

### 2.1 Document Ingestion ✅
- [x] Chunking strategies (fixed size, paragraph-based)
- [x] Document processing pipeline (`DocumentProcessor`)
- [x] Support file types: TXT, MD, PDF, DOCX
- [x] `DocumentExtractor` with unified MIME type handling
- [ ] Background processing (currently synchronous)

### 2.2 Vector Storage (Qdrant) ✅
- [x] `VectorStore` class with Qdrant client
- [x] Collection creation with payload indexes
- [x] Embedding generation (Azure OpenAI text-embedding-3-small)
- [x] Retrieval with ACL filtering (user_id, group_ids, tenant_id)
- [ ] Hybrid search (semantic + keyword)

### 2.3 RAG Pipeline ✅
- [x] `Retriever` class for Qdrant search
- [x] `Embedder` class for Azure OpenAI embeddings
- [x] Context injection in chat endpoints (as first system message)
- [x] Source citations with `[1]`, `[2]` notation and source legend
- [x] Score threshold tuned for `text-embedding-3-large` (0.2 vs 0.5)
- [x] RAG Pipeline documentation (`docs/architecture/RAG-PIPELINE.md`)

### 2.4 Knowledge Base API ✅
- [x] `GET /knowledge-bases` - List accessible KBs
- [x] `POST /knowledge-bases` - Create KB (creates Qdrant collection)
- [x] `GET /knowledge-bases/{id}` - Get KB details
- [x] `DELETE /knowledge-bases/{id}` - Delete KB, documents, and Qdrant collection
- [x] `GET /knowledge-bases/{id}/documents` - List documents in KB
- [x] `POST /knowledge-bases/{id}/documents` - Upload and process documents
- [x] `DELETE /knowledge-bases/{id}/documents/{id}` - Delete document + vectors
- [x] `POST /knowledge-bases/{id}/query` - Direct semantic search
- [x] `GET /knowledge-bases/{id}/cache/stats` - Cache statistics
- [x] `DELETE /knowledge-bases/{id}/cache` - Invalidate cache

### 2.5 Semantic Caching ✅
- [x] `SemanticCache` class with Redis storage
- [x] Cosine similarity matching (configurable threshold)
- [x] Integration with Retriever
- [x] Per-KB cache with TTL and entry limits

---

## Phase 3: Channels (Week 5-6)

**Goal:** Enable access via Slack and Web UI.

### 3.1 Slack Integration
- [ ] Register Slack app
- [ ] Event handling (messages, files)
- [ ] Slash commands
- [ ] Thread-based conversations
- [ ] User identity mapping

### 3.2 Web UI ✅ (Complete)
- [x] Next.js 15 project with React 19
- [x] better-auth with Microsoft EntraID SSO
- [x] SSO cookie forwarding via API proxy route
- [x] Chat interface with streaming
- [x] Session management (sidebar, history)
- [x] Auto-generated conversation titles
- [x] User avatar with initials (handles "Last, First" format)
- [x] Delete/rename conversations
- [x] Session limit (50) with auto-cleanup
- [x] Knowledge Base list page (`/knowledge-bases`)
- [x] Knowledge Base detail page (`/knowledge-bases/[id]`)
- [x] Create KB modal with scope selection
- [x] Document upload with drag-and-drop
- [x] Document list with status badges
- [x] Document deletion
- [x] Knowledge Base deletion (from list and detail pages)
- [x] Navigation from UserMenu dropdown
- [x] Favicon (SVG with gradient)
- [x] KB selector in chat input (pill button + dropdown)
- [x] Selected KBs shown as removable chips
- [x] RAG context injection in chat

---

## Phase 4: Admin & Polish (Week 6)

### 4.1 Admin Features
- [ ] Tool allowlist management
- [ ] Tenant configuration UI
- [ ] Audit log viewer

### 4.2 Production Readiness
- [ ] Grafana dashboards
- [ ] Alerting rules
- [ ] Security review
- [ ] Documentation

---

## Current Status Summary

### What's Working Now

| Feature | Status | How to Test |

|---------|--------|-------------|
| API Server | ✅ | `mise run dev` → http://localhost:8000 |
| Frontend | ✅ | http://localhost:3001 |
| Health Checks | ✅ | `curl http://localhost:8000/health/ready` |
| Azure AI Chat | ✅ | `mise run chat` |
| Streaming | ✅ | POST to `/api/v1/chat/stream` |
| Auth (Dev) | ✅ | Header: `X-Dev-Bypass: true` |
| Auth (SSO) | ✅ | Microsoft EntraID via better-auth |
| Auth (JWT) | ✅ | JWKS verification between frontend/backend |
| SSO Sessions | ✅ | Cookie forwarding via API proxy |
| Rate Limiting | ✅ | TPM + RPM with 429 responses |
| RBAC | ✅ | Permission-based route protection |
| Sessions | ✅ | `GET/POST /api/v1/sessions` |
| Auto-Titles | ✅ | LLM-generated conversation titles |
| User Avatars | ✅ | Initials from SSO name |
| Knowledge Bases | ✅ | Full CRUD `/api/v1/knowledge-bases` |
| KB Browser UI | ✅ | http://localhost:3001/knowledge-bases |
| KB Deletion | ✅ | Delete button on cards and detail page |
| Document Upload | ✅ | Drag-drop or click to upload |
| Document Deletion | ✅ | Delete button in document table |
| KB Selection in Chat | ✅ | Pill button + dropdown in input area |
| RAG Retrieval | ✅ | Chat with `knowledge_base_ids` |
| Database | ✅ | 8 tables via Alembic |
| Docker Stack | ✅ | 9 services (all healthy) |
| Langfuse | ✅ | http://localhost:3000 |

### What's Next
1. ~~**End-to-End RAG Test** — Create KB → upload doc → query with context~~ ✅ **DONE**
2. ~~**KB Selection in Chat UI** — Allow selecting knowledge bases in frontend~~ ✅ **DONE**
3. **Slack Integration** — Bot for team access (Phase 3)
4. **Admin UI** — Tenant/KB management (Phase 4)

---

## Dependencies & Status

| Dependency | Status | Notes |

|------------|--------|-------|
| Azure AI Foundry | ✅ Done | Multi-region (East US, East US 2) |
| EntraID App | ✅ Done | Tenant ID, Client ID, Secret configured |
| PostgreSQL | ✅ Done | Docker, dual-database (langfuse + eai) |
| Qdrant | ✅ Running | v1.13.2 server, qdrant-client 1.16.2 |
| Langfuse | ✅ Running | v3 with ClickHouse |
| Slack Workspace | ⏳ Pending | Needs admin approval |

---

## Infrastructure & Tooling ✅ COMPLETE

### Documentation Reorganization ✅
- [x] Created organized `docs/` hierarchy:
  - `docs/architecture/` — System and component architecture
  - `docs/setup/` — Environment and setup guides
  - `docs/development/` — Contributing and tooling docs
  - `docs/reference/` — Audits and analysis
- [x] Created `docs/README.md` as documentation index
- [x] Updated all cross-references in README.md and frontend/README.md
- [x] Git history preserved via `git mv`

### Project Cleanup ✅
- [x] Removed 14 empty scaffold directories:
  - `spikes/*` (3 dirs), `src/api/middleware/`, `src/agent/{prompts,tools}/`
  - `frontend/src/components/{layout,ui}/`, `deploy/{helm,k8s/*}/`
  - `tests/{unit,integration,e2e}/`, `docs/api/`

### Environment Configuration ✅
- [x] Complete `.env.example` with all 60+ variables
- [x] Documented in `docs/setup/ENVIRONMENT-VARIABLES.md`
- [x] Optional variables properly commented (EASTUS2, LANGFUSE_INIT, OTLP)

### Git Hooks (hk) ✅
- [x] Created `hk.pkl` with pre-commit and commit-msg hooks
- [x] Security checks: detect-private-key, large-files, merge-conflicts
- [x] Linting: ruff (backend), biome (frontend)
- [x] Formatting: trailing-whitespace, eof-fixer
- [x] Commit format: conventional commits validation
- [x] Silent execution (output to /dev/null) to prevent Claude Code crashes
- [x] Manual install via `mise run git:hooks:install`

### CI/CD ✅
- [x] GitHub Actions workflow (`.github/workflows/ci.yml`)
- [x] Backend checks: ruff lint, mypy typecheck, pytest
- [x] Frontend checks: biome lint, tsc typecheck
- [x] Hook validation via `hk run check`
- [x] Env file sync validation (`env-check` job)

### JWT Authentication ✅
- [x] Added better-auth JWT plugin to frontend
- [x] Frontend exposes `/api/auth/jwks` for public key verification
- [x] Frontend exposes `/api/auth/token` for getting JWTs
- [x] Backend verifies JWTs via JWKS (no shared secrets needed)
- [x] Added `jwks` table migration for key storage
- [x] Proper separation: `BETTER_AUTH_*` (frontend) vs `NEXTAUTH_*` (Langfuse)

### Environment File Sync ✅
- [x] Added `mise run env:check` task
- [x] Added `scripts/check-env-sync.sh` validation script
- [x] CI job fails if `.env` and `.env.example` have different variables
- [x] Backend: 64 variables | Frontend: 8 variables

### Docker Structure ✅
- [x] Development Dockerfiles in `dev/`:
  - `Dockerfile.backend` — Hot reload, dev deps, volume mounts
  - `Dockerfile.frontend` — Hot reload, volume mounts
- [x] Production Dockerfiles in `deploy/docker/`:
  - `Dockerfile.backend` — Multi-stage, non-root user, optimized
  - `Dockerfile.frontend` — Multi-stage, standalone output, non-root user

---

## Development Commands

```bash
# First-time setup
mise run setup                # Build containers, start Docker, run migrations
mise run git:hooks:install    # Install git hooks (once after clone)

# Daily development
mise run dev                  # Start everything

# After model changes
mise run db-migrate "description"
mise run db-upgrade

# Testing
mise run chat                 # Quick API test
mise run test                 # Run test suite

# Code quality
mise run check                # Lint + format + typecheck
mise run git:hooks:check      # Run all hook checks manually
mise run git:hooks:fix        # Auto-fix hook issues
mise run env:check            # Verify env files are in sync
```

---

*Document maintained as source of truth for project status.*
