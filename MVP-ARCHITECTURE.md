# MVP Architecture — Enterprise AI Platform

*Working document — evolves as decisions are made.*

## Design Principles

1. **User isolation by default** — Each user gets their own workspace/session
2. **Shareable, not shared by default** — Knowledge bases, documents, chats can be explicitly shared
3. **Opt-in sharing model** — Users/admins control what's shared with whom
4. **On-premise first** — Deploy to own infrastructure; cloud services only for LLM inference
5. **Open source foundation** — No vendor lock-in on core components
6. **Leverage existing infrastructure** — Build on talos-cluster components (Envoy, Langfuse, etc.)

---

## MVP Scope

### In Scope (Phase 1)
- [ ] Single agent per user (isolated workspace)
- [ ] Pre-approved tools only (admin-configured)
- [ ] Personal knowledge base (user uploads docs)
- [ ] Shared org knowledge base (read-only for users)
- [ ] Slack integration (primary channel)
- [ ] Web UI (secondary channel)
- [ ] EntraID SSO login
- [ ] Basic audit logging (admin actions, tool usage)
- [ ] Azure AI Foundry for LLM backend

### Out of Scope (Phase 2+)
- [ ] Department-level knowledge bases
- [ ] Custom agent/workflow building
- [ ] User-connected MCP servers
- [ ] Advanced RBAC (department admins, team leads)
- [ ] SIEM integration
- [ ] A2A (agent-to-agent) orchestration
- [ ] **SDK / API for power users** (design for it now, expose later)

### Design Consideration: API-First Architecture
The platform should be **API-first** from day one. Slack and Web UI are clients of the platform API — the same API that power users (developers, data scientists, DevOps) will use for custom integrations.

**Power user capabilities (Phase 2):**
- Invoke agents programmatically
- CRUD operations on knowledge bases
- Upload/query documents via API
- Trigger tool executions
- Manage sessions
- Register custom MCP servers (elevated users)
- Build custom workflows/automations

**Why design for it now:**
- Ensures clean separation of concerns
- Slack/Web UI become reference implementations
- No "special paths" — everything goes through the API
- Easier to add new clients later (CLI, VS Code extension, etc.)

---

## Proposed Stack

```
┌─────────────────────────────────────────────────────────────────┐
│                         User Interfaces                          │
│                                                                   │
│   ┌─────────────┐    ┌─────────────┐    ┌─────────────┐         │
│   │    Slack    │    │   Web UI    │    │  (Future)   │         │
│   │ Integration │    │             │    │  Embedded   │         │
│   └──────┬──────┘    └──────┬──────┘    └─────────────┘         │
│          │                  │                                    │
└──────────┼──────────────────┼────────────────────────────────────┘
           │                  │
           ▼                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                    API Gateway / Auth Layer                      │
│                                                                   │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │                    EntraID SSO                           │   │
│   │         (OAuth 2.0 / OIDC via Microsoft)                │   │
│   └─────────────────────────────────────────────────────────┘   │
│                                                                   │
│   • User identity & session management                           │
│   • Token validation                                             │
│   • Request routing                                              │
└─────────────────────────────────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────────────────────┐
│                Microsoft Agent Framework                         │
│                  (Core Agent Runtime)                            │
│                                                                   │
│   ┌─────────────┐    ┌─────────────┐    ┌─────────────┐         │
│   │   Agent     │    │   Agent     │    │   Agent     │         │
│   │  (User A)   │    │  (User B)   │    │  (User N)   │         │
│   │             │    │             │    │             │         │
│   │ • Session   │    │ • Session   │    │ • Session   │         │
│   │ • Memory    │    │ • Memory    │    │ • Memory    │         │
│   │ • Tools     │    │ • Tools     │    │ • Tools     │         │
│   └──────┬──────┘    └──────┬──────┘    └──────┬──────┘         │
│          │                  │                  │                 │
│   ┌──────┴──────────────────┴──────────────────┴──────┐         │
│   │              Shared Tool Registry                  │         │
│   │         (Pre-approved tools only)                  │         │
│   └────────────────────────┬───────────────────────────┘         │
│                            │                                     │
└────────────────────────────┼─────────────────────────────────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
        ▼                    ▼                    ▼
┌───────────────┐    ┌───────────────┐    ┌───────────────┐
│  Azure AI     │    │   Qdrant      │    │   Metorial    │
│  Foundry      │    │ (Vector DB)   │    │ (MCP Mgmt)    │
│               │    │               │    │               │
│ • LLM Access  │    │ • Personal KB │    │ • Tool OAuth  │
│ • Native SDK  │    │ • Shared KB   │    │ • MCP Servers │
│ • No proxy    │    │ • ACL filters │    │ • Monitoring  │
└───────────────┘    └───────────────┘    └───────────────┘
```

---

## Component Details

### 1. Authentication Layer

**Technology:** EntraID (Microsoft Entra ID)

**Responsibilities:**
- SSO for all users via OAuth 2.0 / OIDC
- Group membership for RBAC (map Entra groups → permissions)
- Token validation for API requests

**MVP Implementation:**
- Standard EntraID app registration
- MSAL library for token handling
- User claims include: `user_id`, `email`, `groups[]`

---

### 2. Agent Runtime

**Technology:** Microsoft Agent Framework

**Why:**
- Native Azure AI Foundry integration (no LiteLLM proxy needed)
- Built-in EntraID support
- MCP + A2A + OpenAPI tool support
- Enterprise observability (OpenTelemetry)
- Human-in-the-loop approval workflows
- Pluggable memory (Qdrant supported)

**MVP Implementation:**
- One agent instance per user session
- Shared tool registry (pre-approved tools only)
- Declarative agent definitions (YAML)
- Session persistence for conversation continuity

---

### 3. Knowledge Base (RAG)

**Technology:** Qdrant

**Why:**
- Purpose-built vector search
- Excellent metadata filtering (for access control)
- Hybrid search (semantic + keyword)
- Kubernetes-native

**Access Control Model:**
```
Document Chunk Metadata:
{
  "doc_id": "uuid",
  "source": "manual|upload|sync",
  "owner_type": "org|department|user",
  "owner_id": "org-123|dept-456|user-789",
  "visibility": "private|shared",
  "shared_with": ["user-abc", "dept-xyz"],  // explicit shares
  "created_at": "2026-01-31T...",
  "doc_type": "pdf|docx|code|..."
}
```

**Query-time filtering:**
```python
# User can see:
# 1. Org-wide docs (owner_type=org)
# 2. Their own docs (owner_type=user, owner_id=current_user)
# 3. Docs explicitly shared with them (shared_with contains user_id)

filter = {
  "should": [
    {"key": "owner_type", "match": {"value": "org"}},
    {"key": "owner_id", "match": {"value": current_user_id}},
    {"key": "shared_with", "match": {"any": [current_user_id]}}
  ]
}
```

---

### 4. MCP Tool Management

**Technology Options (evaluating):**
1. **Metorial** — Currently evaluating; 600+ integrations, OAuth handling
2. **Microsoft MCP Gateway** — K8s-native, session-aware routing, RBAC

**Note:** Metorial evaluation is in progress. Microsoft MCP Gateway to be evaluated next.

**Responsibilities:**
- MCP server lifecycle management
- OAuth token handling for tool authentication
- Tool discovery and registration
- Usage monitoring and logging

**MVP Implementation:**
- Admin-configured tools only (no user self-service)
- Pre-approved tool allowlist
- Centralized OAuth for tools requiring user auth
- Leverage Envoy AI Gateway MCP support where possible

---

### 5. AI Gateway & LLM Backend

**Technology:** Envoy AI Gateway → Azure AI Foundry (or self-hosted models)

**Why Envoy AI Gateway:**
- Already using Envoy Gateway in talos-cluster
- Native Kubernetes/Gateway API integration
- Supports Azure OpenAI, Anthropic, and 15+ providers
- MCP protocol support (v0.4+)
- OpenTelemetry tracing built-in
- Two-tier gateway pattern for self-hosted + cloud models
- Fully open source (CNCF)

**LLM Options:**
1. **Azure AI Foundry** — GPT-4o, Claude (via Azure)
2. **Self-hosted** — vLLM, Ollama, or other inference servers
3. **Hybrid** — Route to self-hosted for simple queries, cloud for complex

**MVP Implementation:**
- Envoy AI Gateway as unified LLM entry point
- Route to Azure AI Foundry initially
- Per-user token budgets via gateway
- Semantic caching for cost reduction (future)

---

### 6. Observability & Resilience

This section covers the operational concerns: telemetry, tracing, error handling, and fault tolerance.

---

#### 6.1 Telemetry & Metrics

**Technology:** OpenTelemetry → Azure Monitor / Prometheus / Grafana

**Metric Categories:**

| Category | Metrics |

|----------|---------|
| **Request** | Request rate, latency (p50/p95/p99), error rate, status codes |
| **LLM** | Token usage (input/output), model latency, cost per request |
| **RAG** | Query latency, result count, cache hit rate |
| **Tools** | Invocation count, success/failure rate, latency per tool |
| **System** | CPU, memory, pod restarts, queue depth |
| **Business** | Active users, sessions/day, docs uploaded, queries/user |

**Health Checks:**
```
GET /health/live      # Kubernetes liveness (is process alive?)
GET /health/ready     # Kubernetes readiness (can accept traffic?)
GET /health/startup   # Startup probe (is initialization complete?)
```

**Dashboards:**
- Platform overview (requests, errors, latency)
- LLM usage and cost tracking
- Per-user activity (for support/debugging)
- Alerting thresholds

---

#### 6.2 Distributed Tracing

**Technology:** OpenTelemetry (built into MS Agent Framework)

**What to trace:**
```
User Request
  └─► API Gateway (auth, routing)
       └─► Agent Service
            ├─► LLM Call (Azure AI Foundry)
            │    └─► [tokens, latency, model]
            ├─► RAG Query (Qdrant)
            │    └─► [query, results, latency]
            ├─► Tool Invocation (via MCP/Metorial)
            │    └─► [tool, params, result, latency]
            └─► Response Assembly
                 └─► [total latency, status]
```

**Trace Context:**
- Propagate `trace_id` and `span_id` across all service calls
- Include `user_id`, `session_id` in trace context
- Enable correlation of logs ↔ traces ↔ metrics

**Visualization:** Azure Monitor Application Insights, Jaeger, or Grafana Tempo

---

#### 6.3 Circuit Breakers

**Purpose:** Prevent cascading failures when downstream services degrade or fail.

**Where to apply:**

| Dependency | Circuit Breaker Config |

|------------|------------------------|
| **Azure AI Foundry (LLM)** | Threshold: 5 failures in 30s → open for 60s |
| **Qdrant (Vector DB)** | Threshold: 3 failures in 10s → open for 30s |
| **Metorial (MCP)** | Threshold: 5 failures in 30s → open for 60s |
| **External Tools** | Per-tool thresholds, more aggressive |

**States:**
- **Closed:** Normal operation, requests pass through
- **Open:** Requests fail fast, don't hit downstream
- **Half-Open:** Test with limited requests, recover if healthy

**Implementation:**
- .NET: Polly
- Python: tenacity, circuitbreaker
- Service Mesh: Istio (if using)

---

#### 6.4 Error Handling & Boundaries

**Error Boundary Strategy:**

| Layer | Behavior on Failure |

|-------|---------------------|
| **API Gateway** | Return 503 with retry-after header; log error |
| **Agent Service** | Graceful degradation; return partial response if possible |
| **LLM Call** | Retry with backoff (3 attempts); fall back to simpler model if available |
| **RAG Query** | Retry once; respond without RAG context if unavailable |
| **Tool Invocation** | Retry configurable per tool; report tool unavailability to user |

**Retry Policy:**
```
Exponential backoff with jitter:
  - Attempt 1: immediate
  - Attempt 2: 1s + random(0-500ms)
  - Attempt 3: 4s + random(0-1s)
  - Attempt 4: fail / circuit open
```

**User-Facing Errors:**
- Never expose stack traces or internal details
- Provide actionable messages: "The AI service is temporarily unavailable. Please try again in a moment."
- Include request ID for support correlation

**Dead Letter Queue (DLQ):**
- Failed async operations (doc processing, etc.) go to DLQ
- Admin visibility into failed operations
- Retry/replay capability

---

#### 6.5 Rate Limiting & Throttling

**Layers:**

| Layer | Limit | Action |

|-------|-------|--------|
| **Per-user** | 60 requests/min | 429 Too Many Requests |
| **Per-user LLM tokens** | Configurable daily/monthly budget | Soft limit warning, hard limit block |
| **Global** | Protect backend from overload | Queue or reject |

**Implementation:**
- Token bucket or sliding window algorithm
- Redis for distributed rate limit state
- Return `Retry-After` header on 429

---

#### 6.6 Timeouts & Bulkheads

**Timeouts:**

| Operation | Timeout |

|-----------|---------|
| LLM call | 120s (streaming), 60s (non-streaming) |
| RAG query | 10s |
| Tool invocation | 30s (configurable per tool) |
| Total request | 180s max |

**Bulkheads:**
- Isolate thread/connection pools per dependency
- Qdrant failure shouldn't exhaust connections for LLM calls
- Prevents single slow dependency from blocking all requests

---

#### 6.7 Audit Logging (Compliance)

**Technology:** Structured logging → Azure Monitor / ELK / SIEM

**What to log (MVP):**
- User authentication events (login, logout, token refresh)
- Agent session start/end
- Tool invocations (which tool, by whom, when, params — sanitized)
- Document uploads/shares/deletes
- Admin configuration changes
- Access control decisions (allowed/denied)

**Log Format:**
```json
{
  "timestamp": "2026-01-31T18:30:00Z",
  "level": "INFO",
  "event": "tool_invocation",
  "trace_id": "abc123",
  "user_id": "user-456",
  "session_id": "session-789",
  "tool": "web_search",
  "params": { "query": "[REDACTED]" },
  "result": "success",
  "latency_ms": 230
}
```

**Retention:**
- Configurable per log type
- Compliance minimum: 90 days (adjustable for SOC2/other)
- Long-term archive to cold storage

**SIEM Integration:**
- Export via syslog, webhook, or direct integration
- Support for Splunk, Sentinel, ELK, etc.

---

#### 6.8 Alerting

**Critical Alerts (immediate page):**
- Error rate > 10% for 5 minutes
- LLM service unavailable (circuit open)
- Qdrant unavailable (circuit open)
- Auth service unavailable
- Pod crash loops

**Warning Alerts (notify):**
- Latency p95 > 5s for 10 minutes
- LLM token budget > 80% consumed
- DLQ depth > threshold
- Rate limit hits spike
- Certificate expiry < 14 days

**Info Alerts (dashboard only):**
- Deployment completed
- Config changes applied
- Unusual traffic patterns

**Channels:**
- PagerDuty / Opsgenie for critical
- Slack / Teams for warnings
- Dashboard for info

---

### 7. Platform API (Foundation for SDK)

**Architecture Principle:** API-first. All capabilities exposed via REST/GraphQL API.

**MVP API Endpoints:**
```
# Authentication (all endpoints require EntraID token)

# Agent Interaction
POST   /api/v1/chat                    # Send message, get response
POST   /api/v1/chat/stream             # Streaming response (SSE)
GET    /api/v1/sessions                # List user's sessions
GET    /api/v1/sessions/{id}           # Get session history
DELETE /api/v1/sessions/{id}           # End/delete session

# Knowledge Base
GET    /api/v1/knowledge-bases         # List accessible KBs
POST   /api/v1/knowledge-bases/{id}/documents    # Upload document
GET    /api/v1/knowledge-bases/{id}/documents    # List documents
DELETE /api/v1/knowledge-bases/{id}/documents/{doc_id}  # Remove doc
POST   /api/v1/knowledge-bases/{id}/query        # Direct RAG query

# Tools (read-only for standard users)
GET    /api/v1/tools                   # List available tools

# Admin (elevated permissions)
POST   /api/v1/admin/tools             # Add tool to allowlist
DELETE /api/v1/admin/tools/{id}        # Remove tool
POST   /api/v1/admin/knowledge-bases   # Create org/dept KB
PUT    /api/v1/admin/knowledge-bases/{id}/documents  # Add org docs
```

**Phase 2 API Additions (Power Users):**
```
# Custom Workflows
POST   /api/v1/workflows               # Create workflow
GET    /api/v1/workflows               # List workflows
POST   /api/v1/workflows/{id}/execute  # Run workflow

# MCP Server Management (elevated)
POST   /api/v1/mcp-servers             # Register MCP server
GET    /api/v1/mcp-servers             # List registered servers
DELETE /api/v1/mcp-servers/{id}        # Deregister

# Agent Definitions (elevated)
POST   /api/v1/agents                  # Create custom agent
GET    /api/v1/agents                  # List available agents
PUT    /api/v1/agents/{id}             # Update agent definition
```

**Authentication:**
- **User tokens:** EntraID OAuth (for interactive use)
- **Service principals:** EntraID app registrations (for automation)
- **API keys:** Optional, for simpler integrations (scoped, rotatable)

**SDK Strategy (Phase 2):**
- **Python SDK** — Primary, for data science / ML workflows
- **TypeScript/JavaScript SDK** — For web/Node integrations
- **.NET SDK** — For Microsoft ecosystem integrations
- **CLI** — For DevOps/automation scripts

SDKs will be thin wrappers around the REST API with:
- Type-safe request/response models
- Async support
- Streaming helpers
- Auth handling (token refresh, etc.)

**OpenAPI Spec:**
- Auto-generated from API implementation
- Published for SDK generation and documentation
- Enables code generation for additional languages

---

### 8. User Interfaces

#### Slack Integration (Primary)
- Bot responds in DMs and channels
- Slash commands for common actions
- File upload for document ingestion
- Thread-based conversations

#### Web UI (Secondary)
- Chat interface
- Document upload/management
- Knowledge base browser
- Settings/preferences

---

## Deployment

**Platform:** Kubernetes (AKS recommended for Azure stack)

**Components:**
```
┌─────────────────────────────────────────┐
│              Kubernetes Cluster          │
│                                          │
│  ┌────────────┐  ┌────────────┐         │
│  │ API/Auth   │  │  Agent     │         │
│  │ Service    │  │  Service   │         │
│  └────────────┘  └────────────┘         │
│                                          │
│  ┌────────────┐  ┌────────────┐         │
│  │  Qdrant    │  │  Metorial  │         │
│  │  (StatefulSet) │  (if used) │         │
│  └────────────┘  └────────────┘         │
│                                          │
│  ┌────────────┐  ┌────────────┐         │
│  │  Redis     │  │ PostgreSQL │         │
│  │  (Cache)   │  │ (Metadata) │         │
│  └────────────┘  └────────────┘         │
└─────────────────────────────────────────┘
           │
           ▼
    Azure AI Foundry (External)
    EntraID (External)
```

---

## Implementation Patterns (from Microsoft Reference Repos)

Reference: See `MICROSOFT-REPOS-ANALYSIS.md` for full details.

### Rate Limiting Layer

**Source:** `AI-Gateway/labs/token-rate-limiting/`, `AI-Gateway/labs/finops-framework/`

**Implementation:**
```python
# src/core/rate_limiting/token_limiter.py
from redis import Redis
from datetime import datetime

class TokenRateLimiter:
    """Per-tenant token rate limiting with Redis."""
    
    def __init__(self, redis: Redis, default_tpm: int = 100000):
        self.redis = redis
        self.default_tpm = default_tpm
    
    async def check_and_consume(self, tenant_id: str, tokens: int) -> tuple[bool, int]:
        """Check if tokens can be consumed. Returns (allowed, remaining)."""
        minute_key = f"tpm:{tenant_id}:{datetime.utcnow().strftime('%Y%m%d%H%M')}"
        
        # Atomic increment
        pipe = self.redis.pipeline()
        pipe.incrby(minute_key, tokens)
        pipe.expire(minute_key, 120)  # 2 min TTL for safety
        current, _ = await pipe.execute()
        
        limit = await self.get_tenant_limit(tenant_id)
        remaining = max(0, limit - current)
        allowed = current <= limit
        
        return allowed, remaining
    
    async def get_tenant_limit(self, tenant_id: str) -> int:
        """Get TPM limit from tenant config."""
        limit = await self.redis.hget("tenant:limits", tenant_id)
        return int(limit) if limit else self.default_tpm
```

### Semantic Caching Layer

**Source:** `AI-Gateway/labs/semantic-caching/`

**Implementation:**
```python
# src/core/caching/semantic_cache.py
from qdrant_client import QdrantClient
from redis import Redis
import hashlib
import json

class SemanticCache:
    """Cache LLM responses based on semantic similarity of prompts."""
    
    def __init__(self, qdrant: QdrantClient, redis: Redis, 
                 collection: str = "prompt_cache", threshold: float = 0.95):
        self.qdrant = qdrant
        self.redis = redis
        self.collection = collection
        self.threshold = threshold
    
    async def get(self, prompt: str, embedding: list[float], 
                  tenant_id: str) -> dict | None:
        """Look up cached response by semantic similarity."""
        results = await self.qdrant.search(
            collection_name=self.collection,
            query_vector=embedding,
            query_filter={"must": [{"key": "tenant_id", "match": {"value": tenant_id}}]},
            limit=1,
            score_threshold=self.threshold
        )
        
        if results and results[0].score >= self.threshold:
            cache_key = results[0].payload["cache_key"]
            cached = await self.redis.get(f"llm_cache:{cache_key}")
            if cached:
                return json.loads(cached)
        return None
    
    async def set(self, prompt: str, embedding: list[float], 
                  response: dict, tenant_id: str, ttl: int = 3600):
        """Cache response with embedding for semantic lookup."""
        cache_key = hashlib.sha256(prompt.encode()).hexdigest()[:16]
        
        # Store embedding in Qdrant for similarity search
        await self.qdrant.upsert(
            collection_name=self.collection,
            points=[{
                "id": cache_key,
                "vector": embedding,
                "payload": {"cache_key": cache_key, "tenant_id": tenant_id}
            }]
        )
        
        # Store response in Redis
        await self.redis.setex(f"llm_cache:{cache_key}", ttl, json.dumps(response))
```

### Document Chunking Layer

**Source:** `chat-with-your-data/code/backend/batch/utilities/document_chunking/`

**Implementation:**
```python
# src/rag/chunking/strategies.py
from abc import ABC, abstractmethod
from enum import Enum

class ChunkingStrategy(Enum):
    LAYOUT = "layout"           # Document structure aware
    PAGE = "page"               # Page-by-page
    FIXED_SIZE = "fixed_size"   # Token-based with overlap
    PARAGRAPH = "paragraph"     # Semantic paragraphs
    JSON = "json"               # Structured data

class DocumentChunker(ABC):
    @abstractmethod
    async def chunk(self, content: bytes, content_type: str) -> list[dict]:
        """Split document into chunks with metadata."""
        pass

class FixedSizeChunker(DocumentChunker):
    def __init__(self, chunk_size: int = 512, overlap: int = 128):
        self.chunk_size = chunk_size
        self.overlap = overlap
    
    async def chunk(self, content: bytes, content_type: str) -> list[dict]:
        text = await self._extract_text(content, content_type)
        tokens = self._tokenize(text)
        
        chunks = []
        for i in range(0, len(tokens), self.chunk_size - self.overlap):
            chunk_tokens = tokens[i:i + self.chunk_size]
            chunks.append({
                "text": self._detokenize(chunk_tokens),
                "start_idx": i,
                "end_idx": i + len(chunk_tokens),
                "chunk_strategy": "fixed_size"
            })
        return chunks

def get_chunker(strategy: str) -> DocumentChunker:
    """Factory for chunking strategies."""
    strategies = {
        "layout": LayoutChunker(),
        "page": PageChunker(),
        "fixed_size": FixedSizeChunker(),
        "paragraph": ParagraphChunker(),
        "json": JSONChunker()
    }
    return strategies.get(strategy, FixedSizeChunker())
```

### RBAC Pattern

**Source:** `active-directory-aspnetcore-webapp-openidconnect-v2/5-WebApp-AuthZ/`

**Implementation:**
```python
# src/auth/rbac.py
from enum import Enum
from functools import wraps

class AppRole(str, Enum):
    ORG_ADMIN = "OrgAdmin"           # Full platform admin
    DEPT_ADMIN = "DeptAdmin"         # Department admin
    TEAM_LEAD = "TeamLead"           # Team management
    USER = "User"                    # Regular user
    READ_ONLY = "ReadOnly"           # View only

class Permission(str, Enum):
    MANAGE_ORG_KB = "manage_org_kb"
    MANAGE_DEPT_KB = "manage_dept_kb"
    MANAGE_TOOLS = "manage_tools"
    UPLOAD_DOCS = "upload_docs"
    QUERY_KB = "query_kb"
    USE_AGENT = "use_agent"
    VIEW_AUDIT_LOGS = "view_audit_logs"

# Role → Permissions mapping
ROLE_PERMISSIONS = {
    AppRole.ORG_ADMIN: [p for p in Permission],  # All permissions
    AppRole.DEPT_ADMIN: [
        Permission.MANAGE_DEPT_KB, Permission.UPLOAD_DOCS,
        Permission.QUERY_KB, Permission.USE_AGENT
    ],
    AppRole.TEAM_LEAD: [
        Permission.UPLOAD_DOCS, Permission.QUERY_KB, Permission.USE_AGENT
    ],
    AppRole.USER: [Permission.UPLOAD_DOCS, Permission.QUERY_KB, Permission.USE_AGENT],
    AppRole.READ_ONLY: [Permission.QUERY_KB],
}

def require_permission(permission: Permission):
    """Decorator to check user has required permission."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            user = get_current_user()  # From request context
            user_roles = user.get("roles", [])
            
            for role in user_roles:
                if permission in ROLE_PERMISSIONS.get(AppRole(role), []):
                    return await func(*args, **kwargs)
            
            raise PermissionDenied(f"Missing permission: {permission}")
        return wrapper
    return decorator
```

### Usage Tracking (FinOps)

**Source:** `AI-Gateway/labs/finops-framework/`

**Implementation:**
```python
# src/observability/usage_tracker.py
from langfuse import Langfuse
from prometheus_client import Counter, Histogram
import time

# Prometheus metrics
TOKENS_TOTAL = Counter('ai_tokens_total', 'Total tokens', ['tenant_id', 'model', 'type'])
COST_TOTAL = Counter('ai_cost_usd_total', 'Total cost in USD', ['tenant_id', 'model'])
REQUEST_LATENCY = Histogram('ai_request_seconds', 'Request latency', ['tenant_id', 'model'])

class UsageTracker:
    """Track LLM usage for FinOps and cost attribution."""
    
    def __init__(self, langfuse: Langfuse):
        self.langfuse = langfuse
        self.cost_per_token = {
            "gpt-4o": {"input": 0.0025/1000, "output": 0.01/1000},
            "gpt-4o-mini": {"input": 0.00015/1000, "output": 0.0006/1000},
            "claude-3-5-sonnet": {"input": 0.003/1000, "output": 0.015/1000},
        }
    
    async def track(self, tenant_id: str, model: str, 
                    prompt_tokens: int, completion_tokens: int,
                    latency_ms: float, trace_id: str):
        """Record usage metrics."""
        
        # Calculate cost
        costs = self.cost_per_token.get(model, {"input": 0, "output": 0})
        cost_usd = (prompt_tokens * costs["input"]) + (completion_tokens * costs["output"])
        
        # Prometheus metrics
        TOKENS_TOTAL.labels(tenant_id, model, 'input').inc(prompt_tokens)
        TOKENS_TOTAL.labels(tenant_id, model, 'output').inc(completion_tokens)
        COST_TOTAL.labels(tenant_id, model).inc(cost_usd)
        REQUEST_LATENCY.labels(tenant_id, model).observe(latency_ms / 1000)
        
        # Langfuse trace for detailed analytics
        self.langfuse.generation(
            trace_id=trace_id,
            name="llm_call",
            model=model,
            usage={
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": prompt_tokens + completion_tokens
            },
            metadata={
                "tenant_id": tenant_id,
                "cost_usd": cost_usd,
                "latency_ms": latency_ms
            }
        )
```

---

## Development Approach

**AI-assisted development** — Leverage coding assistants (Claude, Copilot, etc.) heavily for:
- Boilerplate and scaffolding
- Integration code
- Test generation
- Documentation

**Phased delivery:**
1. **Spike:** Validate Microsoft Agent Framework + Qdrant integration
2. **Foundation:** Auth layer, basic agent runtime, document upload
3. **RAG:** Knowledge base with access control
4. **Channels:** Slack integration
5. **Polish:** Web UI, audit logging, admin tools

---

## Open Items / Decisions Needed

| Item | Status | Notes |

|------|--------|-------|
| Metorial evaluation | 🔄 In progress | Does it meet MCP management needs? |
| MS Agent Framework spike | ⏳ Not started | Validate Azure AI Foundry + Qdrant integration |
| Slack app registration | ⏳ Not started | Need workspace admin approval |
| EntraID app registration | ⏳ Not started | Need tenant admin |
| Qdrant deployment model | ⏳ Not started | Self-hosted vs Qdrant Cloud |
| Web UI framework | ⏳ Not started | React? Next.js? |

---

## Success Criteria (MVP)

### Functional
- [ ] User can log in via EntraID SSO
- [ ] User can chat with an AI agent
- [ ] User can upload documents to personal knowledge base
- [ ] User can query personal + org knowledge bases
- [ ] User can use pre-approved tools via agent
- [ ] Admin can configure tool allowlist
- [ ] Admin can upload org-wide documents
- [ ] Works in Slack DM
- [ ] Works in web browser
- [ ] **Core API endpoints functional** (foundation for SDK)
- [ ] **OpenAPI spec published** (enables future SDK generation)

### Operational
- [ ] Health check endpoints implemented (live/ready/startup)
- [ ] Distributed tracing functional (trace requests end-to-end)
- [ ] Metrics exported to monitoring system
- [ ] Circuit breakers configured for external dependencies
- [ ] Retry policies implemented with backoff
- [ ] Rate limiting per user enforced
- [ ] Structured audit logging to log aggregator
- [ ] Critical alerts configured and tested
- [ ] Graceful error messages (no stack traces to users)

## Success Criteria (Phase 2 — Power Users)

- [ ] Python SDK published (PyPI)
- [ ] TypeScript SDK published (npm)
- [ ] CLI tool for automation
- [ ] Power users can invoke agents via API
- [ ] Power users can manage knowledge bases via API
- [ ] Elevated users can register custom MCP servers
- [ ] Elevated users can define custom agents/workflows

---

*Document created: 2026-01-31*
*Last updated: 2026-01-31*
