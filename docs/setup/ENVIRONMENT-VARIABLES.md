# Environment Variables Reference

This document provides a complete reference for all environment variables used in the Enterprise AI Platform.

## Quick Start

```bash
# 1. Copy the template
cp dev/.env.example dev/.env

# 2. Generate secure secrets (replace placeholders)
openssl rand -base64 32  # For NEXTAUTH_SECRET, SALT, BETTER_AUTH_SECRET
openssl rand -hex 32     # For ENCRYPTION_KEY (must be 64 hex chars)
openssl rand -base64 24 | tr -d '/+=' | head -c 32  # For passwords

# 3. Fill in your Azure credentials

# 4. Start the stack
mise run dev
```

---

## File Locations

| File | Purpose | Git Tracked? |
|------|---------|--------------|
| `dev/.env.example` | Template with all Docker variables | ✅ Yes |
| `dev/.env` | Your actual Docker secrets | ❌ No |
| `frontend/.env.example` | Template for local frontend dev | ✅ Yes |
| `frontend/.env.local` | Your actual frontend secrets | ❌ No |

> **Note:** The root `.env.example` was removed to avoid confusion. Use `dev/.env.example` as the primary source of truth.

---

## Backend Variables (Python/FastAPI)

These variables are used by `src/core/config.py` via Pydantic Settings.

### Application

| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `ENVIRONMENT` | `development` | No | Environment mode (development/staging/production) |
| `DEBUG` | `false` | No | Enable debug mode |
| `LOG_LEVEL` | `INFO` | No | Logging level (DEBUG/INFO/WARNING/ERROR) |
| `LOG_FORMAT` | `console` | No | Log format (`console` or `json`) |
| `API_HOST` | `0.0.0.0` | No | API server bind address |
| `API_PORT` | `8000` | No | API server port |

### Database (PostgreSQL)

| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `DATABASE_URL` | — | **Yes** | Full PostgreSQL connection string |
| `POSTGRES_HOST` | `localhost` | No | PostgreSQL hostname |
| `POSTGRES_PORT` | `5432` | No | PostgreSQL port |
| `POSTGRES_USER` | `postgres` | No | PostgreSQL username |
| `POSTGRES_PASSWORD` | `postgres` | **Yes** | PostgreSQL password |
| `POSTGRES_DB` | `langfuse` | No | Default database (used by Langfuse) |
| `APP_DB` | `eai` | No | Application database name |

> **Note:** In Docker, `DATABASE_URL` is constructed automatically. For local dev, set it explicitly.

### Redis

| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `REDIS_HOST` | `localhost` | No | Redis hostname |
| `REDIS_PORT` | `6379` | No | Redis port |
| `REDIS_AUTH` | `redissecret` | **Yes** | Redis password |

### Qdrant (Vector Database)

| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `QDRANT_URL` | `http://localhost:6333` | No | Qdrant REST API URL |
| `QDRANT_COLLECTION` | `documents` | No | Default collection name |
| `QDRANT_API_KEY` | — | No | API key (if auth enabled) |

### Azure AI Foundry (Multi-Region)

| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `AZURE_AI_EASTUS_ENDPOINT` | — | **Yes** | East US OpenAI endpoint URL |
| `AZURE_AI_EASTUS_API_KEY` | — | **Yes** | East US API key |
| `AZURE_AI_EASTUS_MODELS` | — | No | Comma-separated model list |
| `AZURE_AI_EASTUS2_ENDPOINT` | — | No | East US 2 endpoint URL |
| `AZURE_AI_EASTUS2_API_KEY` | — | No | East US 2 API key |
| `AZURE_AI_EASTUS2_MODELS` | — | No | Comma-separated model list |
| `AZURE_AI_MODEL_ROUTING` | `{}` | No | JSON: model → region mapping |
| `AZURE_AI_DEFAULT_MODEL` | `gpt-4o-mini` | No | Default model for chat |
| `AZURE_AI_DEFAULT_REGION` | `eastus` | No | Default region |
| `AZURE_OPENAI_API_VERSION` | `2025-04-01-preview` | No | Azure OpenAI API version |

### Embeddings

| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `EMBEDDING_MODEL` | `text-embedding-3-small` | No | Azure embedding model name |
| `EMBEDDING_DIMENSIONS` | `1536` | No | Vector dimensions (must match model) |

Available embedding models:
- `text-embedding-ada-002` → 1536 dims (legacy, lowest cost)
- `text-embedding-3-small` → 1536 dims (recommended)
- `text-embedding-3-large` → 3072 dims (highest quality)

### Microsoft Entra ID (SSO)

| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `AZURE_TENANT_ID` | — | **Yes** | Azure AD tenant ID |
| `AZURE_CLIENT_ID` | — | **Yes** | App registration client ID |
| `AZURE_CLIENT_SECRET` | — | **Yes** | App registration client secret |
| `AZURE_REDIRECT_URI` | `http://localhost:8000/auth/callback` | No | OAuth redirect URI |

### Rate Limiting

| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `RATE_LIMIT_TPM` | `100000` | No | Tokens per minute limit |
| `RATE_LIMIT_RPM` | `60` | No | Requests per minute limit |

### Semantic Caching

| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `SEMANTIC_CACHE_ENABLED` | `true` | No | Enable semantic cache |
| `SEMANTIC_CACHE_THRESHOLD` | `0.95` | No | Similarity threshold |
| `SEMANTIC_CACHE_TTL` | `3600` | No | Cache TTL in seconds |

### Langfuse SDK

| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `LANGFUSE_HOST` | `http://localhost:3000` | No | Langfuse server URL |
| `LANGFUSE_PUBLIC_KEY` | — | **Yes** | Langfuse project public key |
| `LANGFUSE_SECRET_KEY` | — | **Yes** | Langfuse project secret key |

### OpenTelemetry

| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `OTLP_ENDPOINT` | — | No | OTLP collector endpoint |

---

## Frontend Variables (Next.js)

These variables are used by the Next.js frontend.

### Better Auth

| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `BETTER_AUTH_SECRET` | — | **Yes** | Session encryption secret (32+ chars) |
| `BETTER_AUTH_URL` | `http://localhost:3001` | No | Auth base URL |
| `DATABASE_URL` | — | **Yes** | PostgreSQL URL (same DB as backend) |

### Microsoft Entra ID

| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `AZURE_TENANT_ID` | — | **Yes** | Same as backend |
| `AZURE_CLIENT_ID` | — | **Yes** | Same as backend |
| `AZURE_CLIENT_SECRET` | — | **Yes** | Same as backend |

### API Configuration

| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `NEXT_PUBLIC_API_URL` | — | No | Backend API URL (empty = same origin) |
| `BACKEND_URL` | `http://backend:8000` | No | Internal backend URL (Docker) |

### Next.js

| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `NODE_ENV` | `development` | No | Node environment |
| `NEXT_TELEMETRY_DISABLED` | `1` | No | Disable Next.js telemetry |

---

## Infrastructure Variables (Docker Only)

These variables are used by Docker Compose services.

### ClickHouse (Langfuse v3)

| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `CLICKHOUSE_USER` | `clickhouse` | No | ClickHouse username |
| `CLICKHOUSE_PASSWORD` | `clickhouse` | **Yes** | ClickHouse password |

### MinIO (S3 Storage)

| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `MINIO_ROOT_USER` | `minio` | No | MinIO admin username |
| `MINIO_ROOT_PASSWORD` | `miniosecret` | **Yes** | MinIO admin password |

### Langfuse Server

| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `NEXTAUTH_SECRET` | — | **Yes** | NextAuth secret (32+ chars) |
| `NEXTAUTH_URL` | `http://localhost:3000` | No | Langfuse URL |
| `SALT` | — | **Yes** | Password hashing salt |
| `ENCRYPTION_KEY` | — | **Yes** | 64 hex chars encryption key |

### Langfuse Initialization (Optional)

| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `LANGFUSE_INIT_ORG_ID` | — | No | Pre-create organization ID |
| `LANGFUSE_INIT_ORG_NAME` | — | No | Organization name |
| `LANGFUSE_INIT_PROJECT_ID` | — | No | Pre-create project ID |
| `LANGFUSE_INIT_PROJECT_NAME` | — | No | Project name |
| `LANGFUSE_INIT_PROJECT_PUBLIC_KEY` | — | No | Project public API key |
| `LANGFUSE_INIT_PROJECT_SECRET_KEY` | — | No | Project secret API key |
| `LANGFUSE_INIT_USER_EMAIL` | — | No | Admin user email |
| `LANGFUSE_INIT_USER_NAME` | — | No | Admin user name |
| `LANGFUSE_INIT_USER_PASSWORD` | — | No | Admin user password |

---

## Security Best Practices

### Generating Secrets

```bash
# NEXTAUTH_SECRET, SALT, BETTER_AUTH_SECRET (base64, 32+ chars)
openssl rand -base64 32

# ENCRYPTION_KEY (hex, exactly 64 chars)
openssl rand -hex 32

# Passwords (alphanumeric, 32 chars)
openssl rand -base64 24 | tr -d '/+=' | head -c 32
```

### Production Checklist

- [ ] All secrets are randomly generated (not defaults)
- [ ] `ENCRYPTION_KEY` is exactly 64 hex characters
- [ ] `dev/.env` is in `.gitignore` (never commit secrets)
- [ ] Azure credentials are from a production app registration
- [ ] `DEBUG=false` and `LOG_LEVEL=INFO` or higher
- [ ] `NEXT_PUBLIC_SIGN_UP_DISABLED=true` for Langfuse

---

## Troubleshooting

### "BETTER_AUTH_SECRET is missing"
Set `BETTER_AUTH_SECRET` in `dev/.env` or the frontend will fail to start.

### "ENCRYPTION_KEY must be 64 hex characters"
Generate with: `openssl rand -hex 32`

### Database connection fails
Check that `DATABASE_URL` uses the correct hostname:
- Docker: `postgres` (container name)
- Local: `localhost`

### Azure AI returns 401/403
Verify:
1. `AZURE_AI_*_ENDPOINT` includes the full URL
2. `AZURE_AI_*_API_KEY` is correct
3. Model is deployed in Azure AI Foundry
4. Model is listed in `AZURE_AI_*_MODELS`

---

## Reference

- [Azure AI Foundry Setup](./AZURE-AI-FOUNDRY-SETUP.md)
- [Development Setup](./SETUP.md)
- [Docker Compose Config](../dev/docker-compose.yml)
