# Microsoft Repository Analysis for Enterprise AI Platform

**Analysis Date:** 2026-01-31  
**Purpose:** Extract patterns, code, and approaches for on-premise enterprise AI platform  
**Focus:** Self-hosting, avoiding Azure cloud costs, open-source alternatives

---

## Executive Summary

Analyzed 4 Microsoft reference repositories to identify patterns applicable to our enterprise AI platform. Key finding: **Most Azure patterns can be adapted for on-prem** using Keycloak (identity), Envoy (gateway), Redis (caching/rate-limiting), and Qdrant (vector search).

### Repositories Analyzed

| Repository | License | Value | On-Prem Portability |

|------------|---------|-------|---------------------|
| [AI-Gateway](https://github.com/Azure-Samples/AI-Gateway) | MIT | 🔥 Critical | High - patterns extractable |
| [chat-with-your-data](https://github.com/Azure-Samples/chat-with-your-data-solution-accelerator) | CDLA-Permissive | 🔥 Critical | Medium - needs refactoring |
| [active-directory-aspnetcore-webapp](https://github.com/Azure-Samples/active-directory-aspnetcore-webapp-openidconnect-v2) | MIT | High | High - OIDC is standard |
| [openai samples](https://github.com/Azure-Samples/openai) | MIT | Medium | Medium - agent patterns only |

---

## 1. AI-Gateway Patterns (Critical)

**Location:** `~/reference-repos/AI-Gateway/labs/`

### 1.1 Token Rate Limiting

**Pattern:** Per-tenant/subscription token-per-minute (TPM) limits

**Azure Implementation:**
```xml
<!-- labs/finops-framework/products-policy.xml -->
<azure-openai-token-limit 
    counter-key="@(context.Subscription.Id)"
    tokens-per-minute="{tokens-per-minute}" 
    estimate-prompt-tokens="false" 
    remaining-tokens-variable-name="remainingTokens">
</azure-openai-token-limit>
```

**On-Prem Adaptation:**
```python
# Custom middleware using Redis
class TokenRateLimiter:
    def __init__(self, redis_client: Redis):
        self.redis = redis_client
    
    async def check_limit(self, tenant_id: str, tokens: int) -> bool:
        key = f"tpm:{tenant_id}:{datetime.now().strftime('%Y%m%d%H%M')}"
        current = await self.redis.incrby(key, tokens)
        await self.redis.expire(key, 60)  # 1 minute window
        limit = await self.get_tenant_limit(tenant_id)
        return current <= limit
```

**Components Needed:**
- Redis for counters
- Tenant configuration store (PostgreSQL)
- Middleware integration

### 1.2 Semantic Caching

**Pattern:** Cache LLM responses based on semantic similarity of prompts

**Azure Implementation:** Uses Azure Redis + APIM policy

**On-Prem Adaptation:**
```python
# Using Qdrant for similarity + Redis for response cache
class SemanticCache:
    def __init__(self, qdrant: QdrantClient, redis: Redis, threshold: float = 0.95):
        self.qdrant = qdrant
        self.redis = redis
        self.threshold = threshold
    
    async def get_cached(self, prompt: str, embedding: list[float]) -> Optional[str]:
        # Search for similar prompts
        results = await self.qdrant.search(
            collection_name="prompt_cache",
            query_vector=embedding,
            limit=1,
            score_threshold=self.threshold
        )
        if results:
            cache_key = results[0].payload["cache_key"]
            return await self.redis.get(cache_key)
        return None
```

**Components Needed:**
- Qdrant collection for prompt embeddings
- Redis for response storage
- Embedding model (local or API)

### 1.3 FinOps/Cost Tracking

**Pattern:** Token usage metrics → cost attribution → alerts

**Azure Implementation:**
```xml
<!-- labs/finops-framework/policy.xml -->
<azure-openai-emit-token-metric namespace="aiusage">
    <dimension name="Product" value="@(context.Product.Id)" />
</azure-openai-emit-token-metric>
```

**On-Prem Adaptation:**
```python
# Langfuse + Prometheus for observability
from langfuse import Langfuse
from prometheus_client import Counter, Histogram

TOKENS_USED = Counter(
    'ai_tokens_total', 
    'Total tokens consumed',
    ['tenant_id', 'model', 'operation']
)

class UsageTracker:
    def __init__(self, langfuse: Langfuse):
        self.langfuse = langfuse
    
    async def track(self, tenant_id: str, model: str, 
                    prompt_tokens: int, completion_tokens: int,
                    cost_usd: float):
        # Prometheus metrics
        TOKENS_USED.labels(tenant_id, model, 'prompt').inc(prompt_tokens)
        TOKENS_USED.labels(tenant_id, model, 'completion').inc(completion_tokens)
        
        # Langfuse trace for detailed analytics
        self.langfuse.generation(
            name="llm_call",
            model=model,
            usage={
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": prompt_tokens + completion_tokens
            },
            metadata={"tenant_id": tenant_id, "cost_usd": cost_usd}
        )
```

**Components Needed:**
- Langfuse (already in docker-compose)
- Prometheus + Grafana
- Cost configuration per model

### 1.4 Session Awareness

**Pattern:** Multi-turn conversation state across load-balanced backends

**Key Learning:** OpenAI Responses API requires response ID from previous calls. Without session affinity, conversations break.

**On-Prem Implementation:**
- Use Redis for session state (conversation history, response IDs)
- Cookie-based or header-based session routing in Envoy
- Store conversation context in PostgreSQL for persistence

### 1.5 MCP Integration

**Pattern:** Model Context Protocol with credential manager + JWT validation

**Azure Implementation:**
```xml
<!-- labs/mcp-a2a-agents/policy.xml -->
<authentication-managed-identity resource="https://cognitiveservices.azure.com" 
    output-token-variable-name="managed-id-access-token" />
<set-header name="Authorization" exists-action="override">
    <value>@("Bearer " + (string)context.Variables["managed-id-access-token"])</value>
</set-header>
<azure-openai-emit-token-metric namespace="openai">
    <dimension name="User ID" value="@(context.Request.Headers.GetValueOrDefault("x-user-id", "N/A"))" />
</azure-openai-emit-token-metric>
```

**On-Prem Adaptation:**
- Replace managed identity with service account tokens
- Use Keycloak for OAuth token management
- Envoy ext_authz for JWT validation
- Track user_id from JWT claims

### 1.6 Multi-Agent Orchestration (A2A)

**Location:** `labs/mcp-a2a-agents/`

**Pattern:** Heterogeneous agents (Semantic Kernel + AutoGen) communicating via A2A protocol through APIM

**Key Components:**
- Azure Container Apps for agent hosting
- APIM as unified gateway with auth
- MCP servers for tool integration

**On-Prem Adaptation:**
- Kubernetes pods for agents
- Envoy Gateway for routing + auth
- Microsoft MCP Gateway or Metorial for tool management

---

## 2. Chat-with-Your-Data Patterns (Critical)

**Location:** `~/reference-repos/chat-with-your-data-solution-accelerator/`

### 2.1 Document Chunking Strategies

**Location:** `code/backend/batch/utilities/document_chunking/`

```python
# strategies.py - Factory pattern for chunking
def get_document_chunker(chunking_strategy: str):
    strategies = {
        "layout": LayoutDocumentChunking(),      # Document structure aware
        "page": PageDocumentChunking(),           # Page-by-page
        "fixed_size_overlap": FixedSizeOverlapDocumentChunking(),  # Token-based
        "paragraph": ParagraphDocumentChunking(), # Semantic paragraphs
        "json": JSONDocumentChunking()            # Structured data
    }
    return strategies.get(chunking_strategy)
```

**Recommendation:** Extract and adapt all chunking strategies for our RAG pipeline.

### 2.2 Database Factory Pattern

**Location:** `code/backend/batch/utilities/chat_history/database_factory.py`

```python
class DatabaseFactory:
    @staticmethod
    def get_conversation_client():
        if env_helper.DATABASE_TYPE == "CosmosDB":
            return CosmosConversationClient(...)
        elif env_helper.DATABASE_TYPE == "PostgreSQL":
            return PostgresConversationClient(...)
```

**Adaptation:** Use PostgreSQL implementation directly (already our choice).

### 2.3 RAG Architecture

**Key Components:**
- Azure AI Search → **Replace with Qdrant**
- Azure Document Intelligence → **Replace with local processing (Apache Tika, pdf2text)**
- Azure OpenAI → **Use Azure AI Foundry (direct) or local models**

**Reusable Patterns:**
- Conversation flow management
- Context injection
- Source citation handling
- Admin configuration UI

---

## 3. Authentication Patterns (High Value)

**Location:** `~/reference-repos/active-directory-aspnetcore-webapp-openidconnect-v2/`

### 3.1 App Roles Pattern

```csharp
// Infrastructure/AppRoles.cs
public static class AppRole
{
    public const string UserReaders = "UserReaders";
    public const string DirectoryViewers = "DirectoryViewers";
}

public static class AuthorizationPolicies
{
    public const string AssignmentToUserReaderRoleRequired = "AssignmentToUserReaderRoleRequired";
}
```

**Our Roles:**
```csharp
public static class AppRole
{
    public const string OrgAdmin = "OrgAdmin";           // Full platform admin
    public const string DeptAdmin = "DeptAdmin";         // Department admin
    public const string TeamLead = "TeamLead";           // Team management
    public const string User = "User";                   // Regular user
    public const string ReadOnly = "ReadOnly";           // View only
}
```

### 3.2 Startup Configuration

```csharp
// Startup.cs - Key patterns
services.AddMicrosoftIdentityWebAppAuthentication(Configuration)
    .EnableTokenAcquisitionToCallDownstreamApi(scopes)
    .AddInMemoryTokenCaches();  // or Redis/SQL

// Configure role claim type
services.Configure<OpenIdConnectOptions>(options =>
{
    options.TokenValidationParameters.RoleClaimType = "roles";
});

// Policy-based authorization
services.AddAuthorization(options =>
{
    options.AddPolicy("RequireOrgAdmin", 
        policy => policy.RequireRole(AppRole.OrgAdmin));
    options.AddPolicy("RequireDeptAdmin", 
        policy => policy.RequireRole(AppRole.OrgAdmin, AppRole.DeptAdmin));
});
```

### 3.3 Keycloak Adaptation

**EntraID → Keycloak mapping:**
- App Registration → Keycloak Client
- App Roles → Keycloak Roles (realm or client)
- Groups → Keycloak Groups
- Microsoft.Identity.Web → Standard OIDC middleware + Keycloak adapter

---

## 4. Agent Patterns (Medium Value)

**Location:** `~/reference-repos/openai/Agent_Based_Samples/customer_assist/`

### 4.1 Multi-Agent Architecture

**Technology Stack:**

| Capability | Technology |

|------------|------------|
| Orchestration | Semantic Kernel Process Framework |
| Multimodality | Azure AI Services |
| Observability | Application Insights |
| Evaluations | Azure AI Evaluation SDK |
| Models | Azure OpenAI (GPT-4o), DeepSeek |
| Safety | Azure AI Content Safety |
| Knowledge | Azure AI Search |

**On-Prem Alternatives:**

| Capability | On-Prem Alternative |

|------------|---------------------|
| Orchestration | Semantic Kernel (same) |
| Multimodality | Local models + Whisper |
| Observability | Langfuse + Prometheus |
| Evaluations | ragas, DeepEval |
| Models | Azure AI Foundry (direct API) |
| Safety | LLM Guard (self-hosted) |
| Knowledge | Qdrant |

---

## 5. On-Prem Architecture Synthesis

### Component Mapping

| Azure Component | On-Prem Alternative | Status |

|-----------------|---------------------|--------|
| Azure API Management | Envoy AI Gateway | ✅ Ready |
| Azure Redis Cache | Redis (self-hosted) | ✅ Ready |
| Cosmos DB | PostgreSQL | ✅ Ready |
| Azure AI Search | Qdrant | ✅ Ready |
| EntraID | Keycloak | ⏳ Template available |
| Azure OpenAI | Azure AI Foundry (direct) | ⏳ Pending setup |
| Azure Monitor | Langfuse + Prometheus | ✅ Ready |
| Azure Functions | Kubernetes Jobs | ✅ Ready |
| Azure Container Apps | Kubernetes Pods | ✅ Ready |

### Implementation Priority

1. **Phase 1 (MVP Core)**
   - Token rate limiting (Redis middleware)
   - Basic RBAC (Keycloak + JWT)
   - Chat history (PostgreSQL)
   - RAG pipeline (Qdrant + document chunking)

2. **Phase 2 (Enterprise Features)**
   - Semantic caching
   - FinOps/cost tracking (Langfuse)
   - Multi-agent orchestration
   - MCP integration

3. **Phase 3 (Scale)**
   - Session affinity
   - Multi-region routing
   - Advanced guardrails

---

## 6. Extracted Code Artifacts

### Files to Extract/Adapt

```
~/reference-repos/AI-Gateway/
├── labs/token-rate-limiting/     → Rate limiting patterns
├── labs/semantic-caching/        → Caching patterns
├── labs/finops-framework/        → Cost tracking
├── labs/access-controlling/      → Auth patterns
├── labs/mcp-a2a-agents/         → MCP + A2A integration
└── shared/                       → Utility functions

~/reference-repos/chat-with-your-data-solution-accelerator/
├── code/backend/batch/utilities/document_chunking/  → All chunking strategies
├── code/backend/batch/utilities/chat_history/       → PostgreSQL client
└── code/backend/batch/utilities/tools/              → RAG tools

~/reference-repos/active-directory-aspnetcore-webapp-openidconnect-v2/
└── 5-WebApp-AuthZ/5-1-Roles/    → Role-based auth patterns
```

### Recommended Next Steps

1. **Create `src/core/rate_limiting/`** - Port token rate limiting to Python/Redis
2. **Create `src/core/caching/`** - Implement semantic caching with Qdrant
3. **Create `src/rag/chunking/`** - Port document chunking strategies
4. **Create `src/auth/`** - Implement RBAC with Keycloak-compatible OIDC
5. **Update docker-compose** - Add Prometheus, Grafana

---

## 7. Risk Assessment

### Low Risk (Use Directly)
- Document chunking strategies (pure Python, no Azure deps)
- App roles pattern (standard OIDC)
- RAG pipeline logic

### Medium Risk (Requires Adaptation)
- Token rate limiting (replace APIM policy with middleware)
- Semantic caching (replace Azure Redis features)
- MCP integration (credential management differs)

### High Risk (Significant Rework)
- Azure Monitor integration (replace with Prometheus/Grafana)
- Azure AI Search (replace with Qdrant, different query syntax)
- Managed Identity (replace with service accounts)

---

## Appendix: Quick Reference Commands

```bash
# Navigate to reference repos
cd ~/reference-repos

# View AI-Gateway labs
ls AI-Gateway/labs/

# View chunking strategies
cat chat-with-your-data-solution-accelerator/code/backend/batch/utilities/document_chunking/strategies.py

# View auth patterns
cat active-directory-aspnetcore-webapp-openidconnect-v2/5-WebApp-AuthZ/5-1-Roles/Infrastructure/AppRoles.cs
```
