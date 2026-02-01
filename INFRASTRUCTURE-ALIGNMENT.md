# Infrastructure Alignment — Existing Assets & Skills

*Mapping project requirements to existing infrastructure and development resources.*

---

## Existing Infrastructure (MatherlyNet talos-cluster)

**Repository:** https://github.com/MatherlyNet/talos-cluster

Your Kubernetes cluster already has many of the components we need:

### Core Infrastructure (Deployed)

| Component | Status | Notes |

|-----------|--------|-------|
| **Talos Linux** | ✅ Deployed | Immutable, secure K8s OS |
| **FluxCD** | ✅ Deployed | GitOps reconciliation |
| **Cilium** | ✅ Deployed | CNI with kube-proxy replacement |
| **Envoy Gateway** | ✅ Deployed | Gateway API implementation |
| **Cert-Manager** | ✅ Deployed | TLS certificate management |
| **External-DNS** | ✅ Deployed | DNS automation |
| **Cloudflare Tunnel** | ✅ Deployed | External access |

### AI/ML Components (Optional, Available)

| Component | Status | Relevance |

|-----------|--------|-----------|
| **LiteLLM** | 🟡 Optional | LLM proxy — may be replaced by Envoy AI Gateway |
| **Langfuse** | 🟡 Optional | Observability + evaluation + prompt mgmt — HIGH VALUE |

### PoCs (Not Using)

| Component | Status | Notes |

|-----------|--------|-------|
| **MCP-Context-Forge** | ❌ Skip | Was a PoC; didn't meet needs |
| **Obot** | ❌ Skip | Was a PoC; security concerns |

### Other Optional Components

| Component | Status | Potential Use |

|-----------|--------|---------------|
| **Keycloak** | 🟡 Optional | Could supplement/replace EntraID for on-prem |
| **CloudNative-PG** | 🟡 Optional | PostgreSQL operator — useful for metadata/state |
| **Dragonfly** | 🟡 Optional | Redis alternative — caching |

---

## Recommended Component Activation

### High Priority (Enable for MVP)

1. **Langfuse**
   - Observability, tracing, evaluation
   - Prompt management with versioning
   - Human feedback collection
   - Already in your cluster template

2. **MCP Gateway (Evaluate Options)**
   - **Metorial** — Currently evaluating; 600+ integrations
   - **Microsoft MCP Gateway** — K8s-native, session-aware, RBAC
   - Pick one after evaluation

3. **CloudNative-PG**
   - PostgreSQL for metadata, state, audit logs
   - Kubernetes-native operator

### Medium Priority (Evaluate)

1. **Keycloak**
   - If on-prem identity is preferred over EntraID
   - Or as a federation layer to EntraID

2. **Dragonfly**
   - Redis-compatible caching
   - Session state, rate limiting

### Low Priority / Replace

1. **LiteLLM**
   - May be replaced by Envoy AI Gateway
   - Keep if Envoy AI Gateway lacks specific features

2. **Obot**
   - Had security concerns
   - May be replaced by Microsoft Agent Framework

---

## Envoy AI Gateway Integration

**Current:** Envoy Gateway deployed for general ingress

**Addition:** Envoy AI Gateway extends Envoy Gateway for AI workloads

### Features Alignment

| Need | Envoy AI Gateway Support |

|------|--------------------------|
| Azure OpenAI routing | ✅ Supported |
| Multi-provider failover | ✅ Supported |
| MCP protocol | ✅ Supported (v0.4+) |
| Rate limiting | ✅ Via Envoy Gateway |
| OpenTelemetry tracing | ✅ Built-in |
| Token tracking | ✅ Via metrics |
| Semantic caching | ✅ Available |

### Deployment Path

```yaml
# Add to talos-cluster GitOps
# templates/config/kubernetes/apps/ai/envoy-ai-gateway/app/

# Extends existing Envoy Gateway
# No new ingress controller needed
```

---

## Existing Skills Assessment

Skills from `/Users/jason/dev/AutoGPT/.claude/skills/`:

### microsoft-code-reference ⭐ HIGH VALUE
- **Purpose:** Look up Microsoft APIs, find code samples, verify SDK code
- **Uses:** Microsoft Learn MCP Server
- **Relevance:** Essential for any Microsoft SDK development (Agent Framework, Graph API, etc.)
- **Action:** Port to OpenClaw skills or use directly

### microsoft-docs ⭐ HIGH VALUE
- **Purpose:** Query official Microsoft documentation
- **Uses:** Microsoft Learn MCP Server
- **Relevance:** Azure, .NET, M365 documentation access
- **Action:** Port to OpenClaw skills or use directly

### better-icons 🟡 MEDIUM VALUE
- **Purpose:** Search and retrieve icons from 200+ libraries (Iconify)
- **Relevance:** Useful for Web UI development
- **Action:** Available when building frontend

### vercel-react-best-practices 🟡 MEDIUM VALUE
- **Purpose:** React/Next.js performance optimization rules
- **Relevance:** Useful if building Web UI in React/Next.js
- **Action:** Reference when building frontend

---

## Development Resource Strategy

### AI-Assisted Development
Given the "no budget" constraint and need for AI-assisted development:

1. **Use existing OpenClaw (Bot42)** for:
   - Architecture discussions
   - Code generation
   - Documentation
   - Research

2. **Port/enable skills:**
   - microsoft-code-reference → Use MCP server for SDK validation
   - microsoft-docs → Use MCP server for documentation access

3. **Leverage coding agents:**
   - Claude Code (via OpenClaw)
   - GitHub Copilot (if available)
   - OpenCode / Pi Coding Agent

### Recommended MCP Servers to Enable

| MCP Server | Purpose | Priority |

|------------|---------|----------|
| **Microsoft Learn** | API reference, code samples | HIGH |
| **GitHub** | Repo management, issues, PRs | HIGH |
| **Filesystem** | Local file access | HIGH |
| **Kubernetes** | Cluster management | MEDIUM |

---

## Revised Architecture with Existing Assets

```
┌─────────────────────────────────────────────────────────────────────┐
│                         User Interfaces                              │
│              Slack │ Web UI │ API/SDK │ Embedded                    │
└─────────────────────────────────────────────────────────────────────┘
                                  │
┌─────────────────────────────────────────────────────────────────────┐
│                      Envoy Gateway (existing)                        │
│                 + Envoy AI Gateway extension                         │
│   LLM Routing │ MCP Support │ Rate Limiting │ Tracing               │
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
│  MCP Gateway    │     │   RAG Layer     │     │  LLM Providers  │
│                 │     │                 │     │                 │
│ MCP-ContextForge│     │ Qdrant          │     │ Azure AI Foundry│
│ (existing)      │     │                 │     │ (via Envoy AI)  │
└─────────────────┘     └─────────────────┘     └─────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                    Observability (Langfuse - existing)               │
│        Traces │ Evaluations │ Prompt Management │ Feedback          │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Action Items

### Immediate (This Week)
1. [ ] Enable Langfuse in talos-cluster
2. [ ] Enable MCP-Context-Forge in talos-cluster
3. [ ] Deploy Envoy AI Gateway extension
4. [ ] Enable CloudNative-PG for PostgreSQL

### Short-term (Next 2 Weeks)
1. [ ] Complete Metorial evaluation (compare to MCP-Context-Forge)
2. [ ] Spike: Microsoft Agent Framework + Qdrant integration
3. [ ] Port microsoft-code-reference skill to OpenClaw
4. [ ] Define MVP backlog

### Medium-term (Next Month)
1. [ ] EntraID integration (or Keycloak if on-prem preferred)
2. [ ] Slack app development
3. [ ] Web UI scaffolding

---

*Document created: 2026-01-31*
