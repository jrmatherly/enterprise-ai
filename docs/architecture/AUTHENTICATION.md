# Authentication Architecture

**Last Updated:** 2026-02-02

This document describes the authentication and authorization architecture for the Enterprise AI Platform.

---

## Overview

The platform uses a **federated authentication model** with:
- **Frontend:** [better-auth](https://better-auth.com/) with Microsoft EntraID SSO
- **Backend:** JWT validation via JWKS (no shared secrets)
- **Storage:** PostgreSQL for sessions and JWKS keys

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                  User Browser                               │
│                                                                             │
│  1. Visit /chat ──────────►  2. Redirect to EntraID ─────────────────────┐ │
│                                                                           │ │
│  4. Session cookie set  ◄─────  3. OAuth callback with tokens            │ │
└─────────────────────────────────────────────────────────────────────────────┘
                │
                │ Session Cookie (better_auth.session_token)
                ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              Next.js Frontend                               │
│                                                                             │
│  /api/v1/[...path]  (Proxy Route)                                          │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ 1. Validate session cookie via better-auth                         │   │
│  │ 2. Get JWT from /api/auth/token                                    │   │
│  │ 3. Forward request to backend with Authorization: Bearer <JWT>     │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  /api/auth/jwks  (Public JWKS endpoint)                                     │
│  /api/auth/token (Get JWT for current session)                             │
└─────────────────────────────────────────────────────────────────────────────┘
                │
                │ Authorization: Bearer <JWT>
                ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              FastAPI Backend                                │
│                                                                             │
│  Auth Middleware                                                            │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ 1. Extract JWT from Authorization header                           │   │
│  │ 2. Fetch JWKS from frontend (cached 1 hour)                        │   │
│  │ 3. Validate JWT signature using RS256                              │   │
│  │ 4. Extract claims (sub, email, roles, tenant_id)                   │   │
│  │ 5. Inject user into request state                                  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Technology Choices

### Why better-auth?

1. **Modern TypeScript-first library** — Built for Next.js App Router
2. **Built-in JWT plugin** — Generates JWTs with JWKS for backend validation
3. **Multiple OAuth providers** — EntraID, Google, GitHub, etc.
4. **Database-backed sessions** — Persistent, revocable sessions
5. **Active development** — Well-maintained, growing ecosystem

### Why JWKS Verification?

1. **No shared secrets** — Backend doesn't need frontend's auth secret
2. **Standard protocol** — RFC 7517 (JSON Web Key Set)
3. **Key rotation** — Keys can be rotated without backend changes
4. **Scalable** — Works in distributed/multi-instance deployments

### Why RS256?

1. **Asymmetric** — Private key signs, public key verifies
2. **Wide support** — python-jose, Node.js, all major libraries
3. **Compatibility** — python-jose doesn't support Ed25519/OKP

> **Note:** We initially tried EdDSA (Ed25519) but python-jose doesn't support it. RS256 is the most widely compatible choice.

---

## Configuration

### Frontend (better-auth)

```typescript
// frontend/src/lib/auth.ts
import { betterAuth } from "better-auth";
import { jwt } from "better-auth/plugins";
import { Pool } from "pg";

export const auth = betterAuth({
  database: new Pool({
    connectionString: process.env.DATABASE_URL,
  }),

  socialProviders: {
    microsoft: {
      clientId: process.env.AZURE_CLIENT_ID!,
      clientSecret: process.env.AZURE_CLIENT_SECRET!,
      tenantId: process.env.AZURE_TENANT_ID!,
    },
  },

  plugins: [
    jwt({
      // IMPORTANT: Use RS256 for python-jose compatibility
      jwks: {
        keyPairConfig: {
          alg: "RS256",
        },
      },
      // JWT claims
      jwt: {
        issuer: process.env.BETTER_AUTH_URL,
        audience: process.env.BETTER_AUTH_URL,
        expiresIn: 60 * 15, // 15 minutes
        definePayload: async ({ user }) => ({
          sub: user.id,
          email: user.email,
          name: user.name,
        }),
      },
    }),
  ],
});
```

### Backend (FastAPI)

```python
# src/auth/better_auth.py
from jose import jwt, JWTError
from jose.exceptions import JWKError
import httpx
from functools import lru_cache
from datetime import datetime, timedelta

# Cache JWKS for 1 hour
_jwks_cache: dict = {}
_jwks_cache_time: datetime | None = None
JWKS_CACHE_TTL = timedelta(hours=1)

async def get_jwks() -> dict:
    """Fetch JWKS from frontend, with caching."""
    global _jwks_cache, _jwks_cache_time

    now = datetime.now()
    if _jwks_cache and _jwks_cache_time and (now - _jwks_cache_time) < JWKS_CACHE_TTL:
        return _jwks_cache

    # Use internal URL for Docker networking
    jwks_url = f"{settings.better_auth_internal_url}/api/auth/jwks"

    async with httpx.AsyncClient() as client:
        response = await client.get(jwks_url)
        response.raise_for_status()
        _jwks_cache = response.json()
        _jwks_cache_time = now
        return _jwks_cache

async def verify_token(token: str) -> dict:
    """Verify JWT and return claims."""
    jwks = await get_jwks()

    # Decode header to get key ID
    unverified_header = jwt.get_unverified_header(token)
    kid = unverified_header.get("kid")

    # Find matching key
    key = None
    for k in jwks.get("keys", []):
        if k.get("kid") == kid:
            key = k
            break

    if not key:
        raise JWKError("Key ID not found in JWKS")

    # Verify token
    payload = jwt.decode(
        token,
        key,
        algorithms=["RS256"],
        audience=settings.better_auth_url,  # External URL for validation
        issuer=settings.better_auth_url,
    )

    return payload
```

### Environment Variables

```bash
# dev/.env

# Frontend auth (used by better-auth)
BETTER_AUTH_SECRET=<generate with: openssl rand -base64 32>
BETTER_AUTH_URL=http://localhost:3001

# Backend auth (for JWKS fetch and JWT validation)
# Internal URL uses Docker network name
BETTER_AUTH_INTERNAL_URL=http://frontend:3001
# External URL must match JWT issuer/audience
BETTER_AUTH_URL=http://localhost:3001

# Microsoft EntraID (shared by frontend and backend)
AZURE_TENANT_ID=<your-tenant-id>
AZURE_CLIENT_ID=<your-client-id>
AZURE_CLIENT_SECRET=<your-client-secret>
```

---

## Request Flow (Detailed)

### 1. User Login

```
Browser                    Frontend                   EntraID
   │                          │                          │
   │  GET /login              │                          │
   │────────────────────────►│                          │
   │                          │                          │
   │  Redirect to EntraID     │                          │
   │◄────────────────────────│                          │
   │                          │                          │
   │  OAuth flow              │                          │
   │─────────────────────────────────────────────────────►│
   │                          │                          │
   │  Callback with code      │                          │
   │◄─────────────────────────────────────────────────────│
   │                          │                          │
   │  /api/auth/callback/microsoft                       │
   │────────────────────────►│                          │
   │                          │ Exchange code for tokens │
   │                          │─────────────────────────►│
   │                          │                          │
   │                          │ Access + ID tokens       │
   │                          │◄─────────────────────────│
   │                          │                          │
   │  Set-Cookie: session_token                          │
   │◄────────────────────────│                          │
   │                          │                          │
   │  Redirect to /chat       │                          │
   │◄────────────────────────│                          │
```

### 2. Authenticated API Request

```
Browser                Frontend Proxy              Backend
   │                        │                         │
   │  POST /api/v1/chat     │                         │
   │  Cookie: session_token │                         │
   │───────────────────────►│                         │
   │                        │                         │
   │                        │ Validate session        │
   │                        │ (from cookie)           │
   │                        │                         │
   │                        │ GET /api/auth/token     │
   │                        │ (internal call)         │
   │                        │                         │
   │                        │ Got JWT                 │
   │                        │                         │
   │                        │ POST /api/v1/chat       │
   │                        │ Authorization: Bearer   │
   │                        │───────────────────────►│
   │                        │                         │
   │                        │                         │ Validate JWT via JWKS
   │                        │                         │ Extract user claims
   │                        │                         │
   │                        │ Response               │
   │                        │◄───────────────────────│
   │                        │                         │
   │  Response              │                         │
   │◄───────────────────────│                         │
```

---

## Database Schema

better-auth creates these tables automatically:

```sql
-- User accounts (from OAuth)
CREATE TABLE "user" (
    id TEXT PRIMARY KEY,
    name TEXT,
    email TEXT NOT NULL UNIQUE,
    email_verified BOOLEAN DEFAULT FALSE,
    image TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Active sessions
CREATE TABLE "session" (
    id TEXT PRIMARY KEY,
    expires_at TIMESTAMP NOT NULL,
    token TEXT NOT NULL UNIQUE,  -- Session token (cookie value)
    ip_address TEXT,
    user_agent TEXT,
    user_id TEXT NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- OAuth accounts linked to users
CREATE TABLE "account" (
    id TEXT PRIMARY KEY,
    account_id TEXT NOT NULL,
    provider_id TEXT NOT NULL,
    user_id TEXT NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
    access_token TEXT,
    refresh_token TEXT,
    id_token TEXT,
    expires_at TIMESTAMP,
    password TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- JWKS keys for JWT signing
CREATE TABLE "jwks" (
    id TEXT PRIMARY KEY,
    public_key TEXT NOT NULL,
    private_key TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Email verification tokens (optional)
CREATE TABLE "verification" (
    id TEXT PRIMARY KEY,
    identifier TEXT NOT NULL,
    value TEXT NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

---

## Development Bypass

For local development without auth:

```bash
# Add header to skip auth
curl -H "X-Dev-Bypass: true" http://localhost:8000/api/v1/chat ...
```

> **Warning:** Dev bypass only works when explicitly enabled via environment variable. Never enable in production!

---

## Migrations

### Automatic Startup

Both containers run migrations automatically on startup:

**Frontend (better-auth):**
```bash
# dev/Dockerfile.frontend entrypoint
npx better-auth migrate
exec npm run dev
```

**Backend (alembic):**
```bash
# dev/scripts/backend-entrypoint.sh
alembic upgrade head
exec uvicorn src.api.main:app --reload
```

### Manual Migration

```bash
# Frontend (better-auth)
docker exec -it eai-frontend npx better-auth migrate

# Backend (alembic)
docker exec -it eai-backend alembic upgrade head
```

---

## Troubleshooting

### "Key ID not found in JWKS"

**Cause:** Backend can't find the signing key in JWKS.

**Fix:**
1. Ensure `BETTER_AUTH_INTERNAL_URL` uses Docker network name (`http://frontend:3001`)
2. Check that JWKS endpoint responds: `curl http://localhost:3001/api/auth/jwks`
3. Ensure better-auth migrations ran: `docker exec eai-frontend npx better-auth migrate`

### "Invalid audience"

**Cause:** JWT audience doesn't match expected value.

**Fix:**
1. Ensure `BETTER_AUTH_URL` is the same in frontend and backend
2. Both should use `http://localhost:3001` (the external URL)
3. Don't use Docker network name for validation

### "python-jose doesn't support EdDSA"

**Cause:** better-auth configured with EdDSA, but python-jose lacks support.

**Fix:**
1. Change `frontend/src/lib/auth.ts` to use RS256:
   ```typescript
   jwks: {
     keyPairConfig: {
       alg: "RS256",  // Not "EdDSA"
     },
   },
   ```
2. Restart frontend container
3. Clear JWKS cache (restart backend)

### "Failed to load sessions"

**Cause:** Backend API returning 401/500.

**Fix:**
1. Check backend logs: `docker logs eai-backend`
2. Verify JWT flow: frontend proxy should get JWT and forward it
3. Ensure `BETTER_AUTH_INTERNAL_URL` is set in backend container

---

## Security Considerations

1. **Short-lived JWTs (15 min):** Limits exposure if token is leaked
2. **HTTP-only cookies:** Session token not accessible via JavaScript
3. **JWKS caching (1 hour):** Reduces load, enables key rotation
4. **No shared secrets:** Backend validates via public keys
5. **Separate URLs:** Internal Docker URL for JWKS, external for validation

---

## Files Reference

| File | Purpose |

|------|---------|
| `frontend/src/lib/auth.ts` | better-auth configuration |
| `frontend/src/app/api/auth/[...all]/route.ts` | Auth API routes |
| `frontend/src/app/api/v1/[...path]/route.ts` | Backend proxy (adds JWT) |
| `src/auth/better_auth.py` | JWKS fetch and JWT validation |
| `src/auth/middleware.py` | Request middleware |
| `src/core/config.py` | Configuration (auth URLs) |
| `dev/docker-compose.yml` | Container env vars |
| `dev/scripts/backend-entrypoint.sh` | Backend startup |

---

*This document is the source of truth for authentication architecture.*
