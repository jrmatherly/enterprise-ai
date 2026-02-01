# Implementation Plan — Enterprise AI Platform MVP

**Created:** 2026-01-31  
**Last Updated:** 2026-02-01  
**Status:** Phase 1 In Progress

---

## Phase Overview

| Phase | Focus | Duration | Status |
|-------|-------|----------|--------|
| **Phase 0** | Setup & Validation | 1 week | ✅ Complete |
| **Phase 1** | Core Foundation | 2 weeks | 🔄 In Progress |
| **Phase 2** | RAG & Knowledge Bases | 1.5 weeks | ⏳ Not Started |
| **Phase 3** | Channels (Slack + Web) | 1 week | ⏳ Not Started |
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
│   ├── auth/             ✅ Auth middleware
│   ├── core/             ✅ Config, utilities
│   ├── db/               ✅ Models, migrations
│   ├── observability/    🔄 Partial
│   └── rag/              ⏳ Pending
├── alembic/              ✅ Migrations
├── dev/                  ✅ Docker stack
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

### 1.3 Authentication & Authorization 🔄
- [x] OIDC token validation middleware (EntraID)
- [x] Extract user claims from JWT
- [x] Dev bypass mode for testing (`X-Dev-Bypass: true`)
- [ ] RBAC permission checking
- [ ] `@require_permission` decorator
- [ ] Auth integration tests

### 1.4 Rate Limiting ⏳ NEXT
- [ ] Implement `TokenRateLimiter` class
- [ ] Create rate limit middleware for FastAPI
- [ ] Add tenant limit configuration in PostgreSQL
- [ ] Implement 429 response with `Retry-After` header
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

## Phase 2: RAG & Knowledge Bases (Weeks 4-5)

**Goal:** Implement document ingestion and retrieval with access control.

### 2.1 Document Ingestion
- [ ] Chunking strategies (fixed size, paragraph-based)
- [ ] Document processing pipeline
- [ ] Support file types: PDF, DOCX, TXT, MD
- [ ] Background processing

### 2.2 Vector Storage (Qdrant)
- [ ] Create collection with ACL metadata schema
- [ ] Embedding generation (Azure AI or local)
- [ ] Retrieval with access control filters
- [ ] Hybrid search (semantic + keyword)

### 2.3 RAG Pipeline
- [ ] Retriever class for Qdrant
- [ ] Context injection for agent prompts
- [ ] Source citations in responses

### 2.4 Knowledge Base API
- [ ] List accessible knowledge bases
- [ ] Upload documents
- [ ] List/delete documents
- [ ] Direct RAG query endpoint

### 2.5 Semantic Caching
- [ ] `SemanticCache` class
- [ ] Integration with LLM call path
- [ ] Cache hit/miss metrics

---

## Phase 3: Channels (Week 5-6)

**Goal:** Enable access via Slack and Web UI.

### 3.1 Slack Integration
- [ ] Register Slack app
- [ ] Event handling (messages, files)
- [ ] Slash commands
- [ ] Thread-based conversations
- [ ] User identity mapping

### 3.2 Web UI
- [ ] React/Next.js project
- [ ] OIDC login flow
- [ ] Chat interface with streaming
- [ ] Document upload
- [ ] Knowledge base browser

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
| Health Checks | ✅ | `curl http://localhost:8000/health/ready` |
| Azure AI Chat | ✅ | `mise run chat` |
| Streaming | ✅ | POST to `/api/v1/chat/stream` |
| Auth Bypass | ✅ | Header: `X-Dev-Bypass: true` |
| Database | ✅ | 8 tables via Alembic |
| Docker Stack | ✅ | `mise run docker-ps` |
| Langfuse | ✅ | http://localhost:3000 |

### What's Next
1. **Rate Limiting** — Protect API from overuse
2. **Message Persistence** — Store chat history
3. **RBAC** — Role-based access control
4. **RAG Pipeline** — Knowledge base retrieval

---

## Dependencies & Status

| Dependency | Status | Notes |
|------------|--------|-------|
| Azure AI Foundry | ✅ Done | Multi-region (East US, East US 2) |
| EntraID App | ✅ Done | Tenant ID, Client ID, Secret configured |
| PostgreSQL | ✅ Done | Docker, dual-database (langfuse + eai) |
| Qdrant | ✅ Running | Awaiting RAG implementation |
| Langfuse | ✅ Running | v3 with ClickHouse |
| Slack Workspace | ⏳ Pending | Needs admin approval |

---

## Development Commands

```bash
# Daily development
mise run dev              # Start everything

# After model changes
mise run db-migrate "description"
mise run db-upgrade

# Testing
mise run chat             # Quick API test
mise run test             # Run test suite

# Code quality
mise run check            # Lint + format + typecheck
```

---

*Document maintained as source of truth for project status.*
