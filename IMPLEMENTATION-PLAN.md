# Implementation Plan — Enterprise AI Platform MVP

**Created:** 2026-01-31  
**Last Updated:** 2026-02-01  
**Status:** Phase 2 In Progress

---

## Phase Overview

| Phase | Focus | Duration | Status |
|-------|-------|----------|--------|
| **Phase 0** | Setup & Validation | 1 week | ✅ Complete |
| **Phase 1** | Core Foundation | 2 weeks | ✅ Complete |
| **Phase 2** | RAG & Knowledge Bases | 1.5 weeks | 🔄 In Progress |
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

## Phase 2: RAG & Knowledge Bases 🔄 IN PROGRESS

**Goal:** Implement document ingestion and retrieval with access control.

### 2.1 Document Ingestion ✅
- [x] Chunking strategies (fixed size, paragraph-based)
- [x] Document processing pipeline (`DocumentProcessor`)
- [x] Support file types: TXT, MD
- [ ] Support file types: PDF, DOCX (text extraction pending)
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
- [x] Context injection in chat endpoints
- [ ] Source citations in responses

### 2.4 Knowledge Base API ✅
- [x] `GET /knowledge-bases` - List accessible KBs
- [x] `POST /knowledge-bases` - Create KB (creates Qdrant collection)
- [x] `POST /knowledge-bases/{id}/documents` - Upload and process documents
- [x] `DELETE /knowledge-bases/{id}/documents/{id}` - Delete document + vectors
- [x] `POST /knowledge-bases/{id}/query` - Direct semantic search

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

### 3.2 Web UI ✅ (MVP Complete)
- [x] Next.js 15 project with React 19
- [x] better-auth with Microsoft EntraID SSO
- [x] Chat interface with streaming
- [x] Session management (sidebar, history)
- [ ] Document upload UI
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
| Frontend | ✅ | http://localhost:3001 |
| Health Checks | ✅ | `curl http://localhost:8000/health/ready` |
| Azure AI Chat | ✅ | `mise run chat` |
| Streaming | ✅ | POST to `/api/v1/chat/stream` |
| Auth (Dev) | ✅ | Header: `X-Dev-Bypass: true` |
| Auth (SSO) | ✅ | Microsoft EntraID via better-auth |
| Rate Limiting | ✅ | TPM + RPM with 429 responses |
| RBAC | ✅ | Permission-based route protection |
| Sessions | ✅ | `GET/POST /api/v1/sessions` |
| Knowledge Bases | ✅ | `GET/POST /api/v1/knowledge-bases` |
| RAG Retrieval | ✅ | Chat with `knowledge_base_ids` |
| Database | ✅ | 8 tables via Alembic |
| Docker Stack | ✅ | 9 services (all healthy) |
| Langfuse | ✅ | http://localhost:3000 |

### What's Next
1. **PDF/DOCX Extraction** — Support more document types
2. **Semantic Caching** — Cache similar queries
3. **Slack Integration** — Bot for team access
4. **Admin UI** — Tenant/KB management

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
