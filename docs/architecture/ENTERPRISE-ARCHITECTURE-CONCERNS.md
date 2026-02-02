# Enterprise AI Architecture — Concerns & Opportunities

*Research findings on AI Gateways, MCP Gateways, Registries, and other enterprise considerations.*

---

## Executive Summary

Building an enterprise AI platform requires more than just an agent runtime and a vector database. This document identifies **additional architectural layers** that enterprises typically need, based on industry research and emerging patterns.

**Key findings:**
1. **AI Gateway** layer is emerging as critical infrastructure (like API Gateway was for microservices)
2. **MCP Gateway** is a distinct concern from AI Gateway — manages tool/server lifecycle
3. **Security/Guardrails** must be a first-class concern, not bolted on
4. **FinOps/Cost Management** is a major enterprise pain point
5. **Observability** goes beyond tracing — includes evaluation and quality monitoring
6. **Prompt Management** is an emerging discipline requiring governance

---

## 1. AI Gateway / LLM Gateway

### What It Is
A control plane between applications and LLM providers. Think "API Gateway for AI" — routing, security, governance, observability in one layer.

### Why It Matters
- **Unified interface** to multiple LLM providers (OpenAI, Azure, Anthropic, etc.)
- **Governance enforcement** — rate limits, content policies, PII protection
- **Cost control** — token budgets, usage tracking, chargeback
- **Resilience** — failover between providers, caching, retries
- **Security** — prompt injection defense, jailbreak detection

### Key Players

| Product | Type | Key Features | Notes |

|---------|------|--------------|-------|
| **Kong AI Gateway** | Commercial/OSS | Built on Kong Gateway; MCP support; PII sanitization; RAG pipelines | Enterprise-grade, but pricing complexity |
| **Portkey** | Commercial | 1600+ LLM support; guardrails; governance; caching | Strong enterprise features |
| **LiteLLM** | OSS | OpenAI-compatible proxy; 100+ providers | Already using; limited enterprise OSS features |
| **Cloudflare Firewall for AI** | Commercial | Edge-native; prompt filtering; guardrails | SaaS, not self-hosted |

### Recommendation
**Use Envoy AI Gateway** as the AI Gateway layer. It:
- Built on Envoy Gateway (already deployed in talos-cluster!)
- Native Kubernetes/Gateway API integration
- Supports Azure OpenAI, Anthropic, and 15+ providers
- MCP support (announced in v0.4)
- OpenTelemetry tracing built-in
- Two-tier gateway pattern (Tier 1 for auth/routing, Tier 2 for model serving)
- CNCF project, fully open source
- Integrates with Cilium CNI (already using)

**Existing Infrastructure:** MatherlyNet talos-cluster already has:
- Envoy Gateway deployed
- LiteLLM (optional component)
- Langfuse (optional component)
- MCP-Context-Forge (optional component)
- Obot (optional component)

### Architecture Position
```
┌─────────────────────────────────────────────────────────┐
│                    AI Gateway                            │
│  (Kong AI Gateway / Portkey / LiteLLM)                  │
│                                                          │
│  • Unified LLM API        • Rate limiting               │
│  • Provider routing       • Token budgets               │
│  • Caching               • Guardrails                   │
│  • Failover              • PII sanitization             │
└─────────────────────────────────────────────────────────┘
                            │
         ┌──────────────────┼──────────────────┐
         │                  │                  │
         ▼                  ▼                  ▼
   Azure AI Foundry    Anthropic API    Fallback Provider
```

---

## 2. MCP Gateway & Registry

### What It Is
A management layer specifically for **Model Context Protocol servers** — tool discovery, routing, lifecycle management, OAuth handling.

**Distinct from AI Gateway:** AI Gateway handles LLM traffic; MCP Gateway handles tool/server traffic.

### Why It Matters
- **Tool sprawl** — Enterprises will have dozens/hundreds of MCP servers
- **OAuth complexity** — Each tool may need user OAuth tokens
- **Discovery** — Agents need to find available tools dynamically
- **Governance** — Who can use which tools? Audit trail?
- **Lifecycle** — Deploy, update, scale, retire MCP servers

### Key Players

| Product | Source | Key Features | Notes |

|---------|--------|--------------|-------|
| **Microsoft MCP Gateway** | Microsoft (OSS) | K8s-native; session-aware routing; RBAC; tool registration | Strong fit for our K8s + Microsoft stack |
| **IBM ContextForge** | IBM (OSS) | Federation; multi-protocol; REST-to-MCP; Admin UI; OpenTelemetry | Feature-rich; FastAPI-based |
| **Metorial** | Metorial (OSS) | 600+ integrations; OAuth handling; monitoring | Currently evaluating |
| **Docker MCP Gateway** | Docker (OSS) | Orchestrates MCP servers; credential management | Docker-centric |

### Recommendation
**Evaluate Microsoft MCP Gateway** alongside Metorial:
- Kubernetes-native (aligns with deployment model)
- Session-aware stateful routing (important for agent conversations)
- RBAC built-in
- From Microsoft (ecosystem alignment)
- Tool registration with dynamic routing

### Architecture Position
```
┌─────────────────────────────────────────────────────────┐
│                    MCP Gateway                           │
│     (Microsoft MCP Gateway / IBM ContextForge)          │
│                                                          │
│  • Tool registry          • OAuth token management      │
│  • Session-aware routing  • RBAC / access control       │
│  • Lifecycle management   • Audit logging               │
│  • Dynamic discovery      • Multi-protocol support      │
└─────────────────────────────────────────────────────────┘
                            │
         ┌──────────────────┼──────────────────┐
         │                  │                  │
         ▼                  ▼                  ▼
   MCP Server A       MCP Server B       MCP Server N
   (GitHub)           (Slack)            (Custom)
```

---

## 3. Security & Guardrails

### What It Is
Protective layers that inspect, filter, and sanitize AI inputs/outputs to prevent attacks and data leakage.

### Why It Matters
- **Prompt injection** — Attackers manipulate prompts to bypass controls
- **Jailbreaking** — Users trick models into harmful outputs
- **PII leakage** — Sensitive data exposed in prompts or responses
- **Data exfiltration** — Confidential info sent to external models
- **Compliance** — Regulated industries need content controls

### Key Players

| Product | Type | Key Features | Notes |

|---------|------|--------------|-------|
| **Lakera Guard** | Commercial | Real-time; prompt injection; PII; jailbreak detection | Single API call integration |
| **LLM Guard** | OSS (ProtectAI) | Scanners for PII, secrets, prompt injection | Self-hosted; extensible |
| **Imperva AI Security** | Commercial | SaaS reverse proxy; prompt leakage prevention | Enterprise SaaS |
| **Cloudflare Firewall for AI** | Commercial | Edge-native; policy enforcement | SaaS |
| **Azure AI Content Safety** | Microsoft | Built into Azure AI Foundry | Native if using Azure |

### Recommendation
**Layer defense in depth:**
1. **Azure AI Content Safety** — Native integration with Azure AI Foundry (first line)
2. **LLM Guard (OSS)** — Self-hosted scanner for PII, secrets, prompt injection (second line)
3. **AI Gateway guardrails** — Kong/Portkey built-in guardrails (third line)

### Security Checklist

| Threat | Mitigation |

|--------|------------|
| Prompt injection | Input validation; delimiters; LLM Guard scanners |
| Jailbreaking | Content safety filters; output validation |
| PII leakage (input) | PII detection/redaction before LLM |
| PII leakage (output) | Output scanning; masking |
| Data exfiltration | DLP integration; content classification |
| Unauthorized tool use | RBAC; tool allowlists; audit logging |
| Credential theft | OAuth with short-lived tokens; no secrets in prompts |

---

## 4. FinOps / Cost Management

### What It Is
Financial governance for AI workloads — tracking, budgeting, allocation, and optimization of LLM/AI spend.

### Why It Matters
- **AI costs are unpredictable** — Token-based pricing varies wildly
- **85% of companies miss AI forecasts by >10%** (industry research)
- **Chargeback/showback** — Who's paying for which usage?
- **Budget enforcement** — Prevent runaway costs
- **Optimization** — Are we using the right models for each task?

### Key Capabilities Needed

| Capability | Description |

|------------|-------------|
| **Token tracking** | Per-request input/output token counts |
| **Cost attribution** | Map costs to users, departments, projects |
| **Budget alerts** | Warn when approaching/exceeding budgets |
| **Showback reports** | Visibility into who's using what |
| **Chargeback** | Actual cost allocation to cost centers |
| **Model optimization** | Suggest cheaper models for simple tasks |
| **Caching ROI** | Track cache hit rates and savings |

### Implementation Approach

1. **AI Gateway handles token tracking** — Kong/Portkey/LiteLLM all provide this
2. **Store usage data** — PostgreSQL or data warehouse
3. **Build cost attribution** — Join usage with user/department metadata
4. **Dashboard** — Grafana or custom for visibility
5. **Budget enforcement** — Soft limits (warn) and hard limits (block)

### Architecture Addition
```
┌─────────────────────────────────────────────────────────┐
│                  FinOps / Cost Layer                     │
│                                                          │
│  • Token metering         • Budget enforcement          │
│  • Cost attribution       • Showback/chargeback         │
│  • Usage dashboards       • Optimization recommendations │
└─────────────────────────────────────────────────────────┘
         │
         ▼
   AI Gateway (token tracking) → Usage DB → Reports/Alerts
```

---

## 5. Observability & Evaluation

### Beyond Tracing
Standard observability (traces, metrics, logs) is table stakes. Enterprise AI also needs:

- **Evaluation** — Is the AI giving good answers?
- **Quality monitoring** — Drift detection, regression alerts
- **Human feedback** — Capture thumbs up/down, annotations
- **A/B testing** — Compare prompt/model configurations

### Key Players

| Product | Type | Key Features | Notes |

|---------|------|--------------|-------|
| **Langfuse** | OSS | Tracing; evaluation; prompt management; human feedback | Strong OSS option |
| **Arize Phoenix** | OSS | LLM observability; RAG debugging; evaluations | Strong on RAG |
| **LangWatch** | Commercial | Agent testing with simulations; scenario evaluation | Agent-focused |
| **Arize AX** | Commercial | Enterprise prompt management + observability | Full platform |

### Recommendation
**Langfuse** as the observability/evaluation layer:
- Open source, self-hostable
- OpenTelemetry compatible
- Prompt management with versioning
- Human annotation workflows
- Evaluation framework (LLM-as-judge, custom)
- Integrates with MS Agent Framework via OpenTelemetry

### Evaluation Strategy

| Level | What to Evaluate | Method |

|-------|------------------|--------|
| **Response quality** | Relevance, accuracy, helpfulness | LLM-as-judge; human review |
| **RAG quality** | Retrieval relevance, context usage | Retrieval metrics; LLM-as-judge |
| **Tool usage** | Correct tool selection, parameter accuracy | Deterministic checks |
| **Trajectory** | Was the multi-step reasoning sound? | Step-by-step evaluation |
| **Safety** | Harmful content, policy violations | Classifier; human review |

---

## 6. Prompt Management

### What It Is
Treating prompts as managed artifacts — versioned, tested, reviewed, deployed through a governed process.

### Why It Matters
- **Prompts are code** — They define system behavior
- **Versioning** — Track changes, rollback if needed
- **Testing** — Validate prompts before deployment
- **Collaboration** — Non-engineers contribute to prompts
- **Governance** — Approval workflows for production prompts

### Key Capabilities

| Capability | Description |

|------------|-------------|
| **Version control** | Git-like history for prompts |
| **Templating** | Variables, conditionals, includes |
| **Environment promotion** | Dev → Staging → Production |
| **A/B testing** | Compare prompt variants |
| **Access control** | Who can edit production prompts? |
| **Audit trail** | Who changed what, when |

### Implementation Approach

**Option 1: Langfuse Prompt Management**
- Built into Langfuse (already recommended for observability)
- Versioning, deployment, A/B testing
- API access for runtime retrieval

**Option 2: Git-based with CI/CD**
- Store prompts in Git (YAML/JSON)
- CI/CD pipeline validates and deploys
- More familiar to engineering teams

### Recommendation
Start with **Langfuse Prompt Management** for:
- Unified observability + prompts
- Non-engineer friendly UI
- Built-in evaluation integration

Graduate to Git-based if engineering governance becomes priority.

---

## 7. Additional Enterprise Concerns

### 7.1 Data Governance & Lineage

| Concern | Consideration |

|---------|---------------|
| **Data classification** | What sensitivity level is each knowledge base? |
| **Lineage tracking** | Where did this RAG result come from? |
| **Retention policies** | How long to keep conversation history? |
| **Right to deletion** | Can we purge a user's data on request? |
| **Cross-border data** | Where is data stored/processed? |

### 7.2 Multi-Tenancy & Isolation

| Model | Description | Use Case |

|-------|-------------|----------|
| **Logical isolation** | Shared infra, data separated by tenant ID | Most common; cost-efficient |
| **Namespace isolation** | K8s namespaces per tenant | Moderate isolation |
| **Cluster isolation** | Separate K8s cluster per tenant | High security requirements |

**Recommendation:** Start with logical isolation (tenant ID in all data), design for namespace isolation if needed later.

### 7.3 Disaster Recovery & Business Continuity

| Component | DR Strategy |

|-----------|-------------|
| **Vector DB (Qdrant)** | Replication; backup to object storage |
| **Conversation history** | PostgreSQL with replication |
| **Configuration** | GitOps; declarative infra |
| **LLM provider** | Failover to secondary provider |
| **MCP servers** | Stateless; K8s handles restarts |

**RTO/RPO targets:** Define based on business criticality.

### 7.4 Change Management

| Change Type | Process |

|-------------|---------|
| **Prompt changes** | Review → Test → Staged rollout |
| **Model changes** | Evaluation → A/B test → Gradual rollout |
| **Tool additions** | Security review → Limited rollout → General availability |
| **Config changes** | GitOps; PR review; automated deployment |

### 7.5 Integration with Enterprise Systems

| System | Integration Point |

|--------|-------------------|
| **ITSM (ServiceNow)** | Incident creation for alerts; change requests |
| **IAM (EntraID)** | User identity; group membership |
| **SIEM (Sentinel/Splunk)** | Audit log forwarding |
| **Data Catalog** | Knowledge base metadata |
| **Secrets Manager** | API keys, OAuth credentials |

### 7.6 SLA Management

| Metric | Target (Example) |

|--------|------------------|
| **Availability** | 99.9% uptime |
| **Response latency** | p95 < 5s for chat |
| **Error rate** | < 1% of requests |
| **Recovery time** | < 15 min for critical issues |

### 7.7 Vendor Management

| Vendor | Risk | Mitigation |

|--------|------|------------|
| **Azure AI Foundry** | Outage; pricing changes | Monitor; budget alerts; evaluate alternatives |
| **Qdrant** | Breaking changes | Pin versions; test upgrades |
| **OSS dependencies** | Abandonment | Fork capability; evaluate alternatives |

---

## 8. Revised Architecture Layers

Based on this research, the full enterprise architecture includes:

```
┌─────────────────────────────────────────────────────────────────────┐
│                         User Interfaces                              │
│              Slack │ Web UI │ API/SDK │ Embedded                    │
└─────────────────────────────────────────────────────────────────────┘
                                  │
┌─────────────────────────────────────────────────────────────────────┐
│                      API Gateway / Auth                              │
│                 EntraID SSO │ RBAC │ Rate Limiting                  │
└─────────────────────────────────────────────────────────────────────┘
                                  │
┌─────────────────────────────────────────────────────────────────────┐
│                         AI Gateway                                   │
│   (Kong AI Gateway / LiteLLM)                                       │
│   Unified LLM API │ Guardrails │ Token Tracking │ Caching           │
└─────────────────────────────────────────────────────────────────────┘
                                  │
┌─────────────────────────────────────────────────────────────────────┐
│                    Agent Runtime Layer                               │
│              Microsoft Agent Framework                               │
│   Sessions │ Memory │ Tool Orchestration │ Human-in-the-Loop        │
└─────────────────────────────────────────────────────────────────────┘
                                  │
         ┌────────────────────────┼────────────────────────┐
         │                        │                        │
┌────────▼────────┐     ┌────────▼────────┐     ┌────────▼────────┐
│   MCP Gateway   │     │   RAG Layer     │     │  LLM Providers  │
│                 │     │                 │     │                 │
│ MS MCP Gateway  │     │ Qdrant          │     │ Azure AI Foundry│
│ Tool Registry   │     │ Access Control  │     │ (via AI Gateway)│
│ OAuth Handling  │     │ Multi-tier KB   │     │                 │
└────────┬────────┘     └─────────────────┘     └─────────────────┘
         │
    ┌────┴────┐
    │         │
┌───▼───┐ ┌───▼───┐
│MCP Srv│ │MCP Srv│ ...
└───────┘ └───────┘

┌─────────────────────────────────────────────────────────────────────┐
│                    Cross-Cutting Concerns                            │
├─────────────────┬─────────────────┬─────────────────┬───────────────┤
│ Observability   │ Security        │ FinOps          │ Governance    │
│ (Langfuse)      │ (LLM Guard)     │ (Cost Tracking) │ (Prompts/Audit│
│ Traces │ Evals  │ PII │ Injection │ Budgets │ Alloc │ Versions │ Logs│
└─────────────────┴─────────────────┴─────────────────┴───────────────┘
```

---

## 9. Prioritized Recommendations

### Must Have (MVP)
1. ✅ Agent Runtime (MS Agent Framework)
2. ✅ Vector DB (Qdrant)
3. ✅ Identity (EntraID)
4. ✅ Basic observability (OpenTelemetry → Azure Monitor)
5. ✅ API-first design

### Should Have (Phase 2)
1. **AI Gateway** — Kong AI Gateway or enhanced LiteLLM
2. **MCP Gateway** — Microsoft MCP Gateway
3. **Guardrails** — LLM Guard + Azure Content Safety
4. **Evaluation** — Langfuse
5. **Cost tracking** — Token metering + dashboards
6. **SDK/API** for power users

### Nice to Have (Phase 3+)
1. **Prompt Management** — Langfuse or Git-based
2. **Advanced FinOps** — Chargeback, optimization
3. **Agent marketplace** — Internal catalog of approved agents
4. **A/B testing** — Prompt/model experiments
5. **Advanced DR** — Multi-region, automated failover

---

## 10. Open Questions for Discussion

1. **AI Gateway selection** — Kong vs enhanced LiteLLM vs build custom?
2. **MCP Gateway** — Microsoft MCP Gateway vs Metorial vs both?
3. **Guardrails priority** — How aggressive on security layer before MVP?
4. **FinOps scope** — Showback only for MVP, or full chargeback?
5. **Observability depth** — Langfuse for evaluation, or Azure-native only?

---

*Document created: 2026-01-31*
*Research sources: Industry publications, vendor documentation, GitHub repositories*
