# Dependency Audit Report
**Date**: February 2, 2026  
**Platform**: Enterprise AI Platform

---

## Executive Summary

| Category | Status |

|----------|--------|
| Python Backend | ✅ **All packages current** |
| Frontend (npm) | ⚠️ **Updates needed** (security + features) |
| Docker Services | ⚠️ **Pin versions + minor updates** |

---

## 🔴 Critical Security Issues

### Next.js Vulnerabilities (MUST FIX)

| CVE | Severity | Description |

|-----|----------|-------------|
| CVE-2025-66478 | **CRITICAL (10.0)** | RCE via React Server Components |
| CVE-2025-55184 | High | DoS in React Server Components |
| CVE-2025-55183 | Medium | Source Code Exposure |

**Action**: Upgrade to Next.js `16.1.6` immediately

### PrismJS Vulnerability

| CVE | Severity | Description |

|-----|----------|-------------|
| GHSA-x7hr-w5r2-h6wg | Moderate | DOM Clobbering vulnerability |

**Action**: Upgrade `react-syntax-highlighter` to `16.1.0`

---

## Python Backend Status ✅

All packages are current. `uv sync` keeps lockfile up to date.

| Package | Installed | Latest | Notes |

|---------|-----------|--------|-------|
| fastapi | 0.128.0 | 0.128.0 | ✅ |
| uvicorn | 0.40.0 | 0.40.0 | ✅ |
| sqlalchemy | 2.0.46 | 2.0.46 | ✅ |
| asyncpg | 0.31.0 | 0.31.0 | ✅ |
| redis | 7.1.0 | 7.1.0 | ✅ |
| qdrant-client | 1.16.2 | 1.16.2 | ✅ |
| openai | 2.16.0 | 2.16.0 | ✅ |
| azure-identity | 1.25.1 | 1.25.1 | ✅ |
| azure-ai-projects | 2.0.0b3 | 2.0.0b3 | Beta |
| pydantic | 2.12.5 | 2.12.5 | ✅ |
| langfuse | 3.12.1 | 3.12.1 | ✅ |

### pyproject.toml Recommendations
Update minimum version constraints to prevent accidental downgrades:

```toml
# Current constraints are good, but could be tightened:
"fastapi>=0.128.0",
"qdrant-client>=1.16.0,<1.17.0",  # Pin to match server
```

---

## Frontend Package Updates ⚠️

### Priority 1: Security Fixes (Do Now)

```json
{
  "next": "^16.1.6",
  "react-syntax-highlighter": "^16.1.0"
}
```

### Priority 2: Feature Updates (Safe)

```json
{
  "react": "^19.2.4",
  "react-dom": "^19.2.4",
  "better-auth": "^1.4.18",
  "@tanstack/react-query": "^5.90.20",
  "zustand": "^5.0.11",
  "lucide-react": "^0.563.0",
  "typescript": "^5.9.0",
  "@types/node": "^25.2.0"
}
```

### Priority 3: Major Migrations (Plan Separately)

| Package | Current | Latest | Migration Effort |

|---------|---------|--------|------------------|
| tailwindcss | 3.4.x | 4.1.x | **HIGH** - CSS-first config, breaking changes |
| tailwind-merge | 2.5.x | 3.4.x | Medium - API changes |
| react-markdown | 9.x | 10.x | Medium - Breaking changes |

#### Tailwind CSS v4 Migration Notes
- Configuration moves from `tailwind.config.ts` to CSS `@theme` blocks
- Automatic content detection (no `content: []` needed)
- Native CSS variables for all design tokens
- Requires Vite plugin for best performance
- **Recommendation**: Defer until MVP complete

---

## Docker Services ⚠️

### Current vs Recommended

| Service | Current | Recommended | Action |

|---------|---------|-------------|--------|
| postgres | `17-alpine` | `17-alpine` | ✅ Keep (17 is LTS) |
| redis | `7-alpine` | `7-alpine` | ✅ Keep (8.x has breaking changes) |
| qdrant | `v1.16.2` | `v1.16.2` | ✅ Current |
| clickhouse | `latest` | `25.4-alpine` | ⚠️ **Pin version!** |
| minio | `latest` | `RELEASE.2026-01-15T00-00-00Z` | ⚠️ **Pin version!** |
| langfuse | `3` | `3` | ✅ Current |

### Why Pin Versions?
Using `latest` in production is dangerous:
- No reproducible builds
- Unexpected breaking changes
- Difficult rollback
- Container restarts pull new versions

---

## Recommended Update Strategy

### Phase 1: Security (Do Today)
```bash
cd frontend
npm install next@16.1.6 react-syntax-highlighter@16.1.0
npm audit
```

### Phase 2: Minor Updates (This Week)
```bash
npm install react@19.2.4 react-dom@19.2.4 \
  better-auth@1.4.18 \
  @tanstack/react-query@5.90.20 \
  zustand@5.0.11 \
  lucide-react@0.563.0
```

### Phase 3: Docker Pinning (This Week)
Update `docker-compose.yml`:
```yaml
clickhouse:
  image: clickhouse/clickhouse-server:25.4-alpine

minio:
  image: minio/minio:RELEASE.2026-01-15T00-00-00Z
```

### Phase 4: Major Migrations (Post-MVP)
- Tailwind CSS v4 migration
- react-markdown v10 migration
- tailwind-merge v3 migration

---

## Compatibility Matrix

| Component | Required By | Constraint |

|-----------|-------------|------------|
| qdrant-client 1.16.x | qdrant server 1.16.x | Major+minor must match |
| better-auth 1.4.x | Next.js 15+ / 16+ | Compatible |
| React 19.x | Next.js 16.x | Required |
| Node.js 20+ | Next.js 16.x | Required |

---

## Lockfile Management

### Python (uv)
```bash
# Update all packages to latest compatible
uv sync --upgrade

# Update specific package
uv add package@latest
```

### Node.js (npm)
```bash
# Check for updates
npm outdated

# Update within semver constraints
npm update

# Update with major version changes
npm install package@latest
```

---

---

## Breaking Changes Implemented ✅

### 1. Next.js 15 → 16 Migration

**middleware.ts → proxy.ts**
- Renamed `src/middleware.ts` → `src/proxy.ts`
- Renamed exported function `middleware` → `proxy`
- proxy.ts runs on Node.js runtime (not Edge)
- Updated docker-compose to allow tsconfig.json writes (Turbopack requirement)

```typescript
// Before: middleware.ts
export function middleware(request: NextRequest) { ... }

// After: proxy.ts  
export function proxy(request: NextRequest) { ... }
```

**Turbopack Default**
- Turbopack is now the default bundler
- No code changes needed - Just works™

### 2. react-markdown → streamdown

**Why streamdown?**
- Drop-in replacement for react-markdown
- Built specifically for AI streaming use cases
- Handles incomplete/unterminated markdown gracefully
- Better code syntax highlighting via Shiki

**Changes Made:**
- Uninstalled: `react-markdown`, `react-syntax-highlighter`, `@types/react-syntax-highlighter`
- Installed: `streamdown`, `@streamdown/code`, `@tailwindcss/typography`
- Updated: `MessageBubble.tsx`, `StreamingMessage.tsx`
- Updated: `tailwind.config.ts` (added typography plugin + streamdown content)

```tsx
// Before
import ReactMarkdown from 'react-markdown';
<ReactMarkdown>{content}</ReactMarkdown>

// After
import { Streamdown } from 'streamdown';
import { code } from '@streamdown/code';
<Streamdown plugins={{ code }} isAnimating={isStreaming}>
  {content}
</Streamdown>
```

### 3. Docker Volume Mount

**tsconfig.json mount**
- Changed from `:ro` (read-only) to writable
- Required because Turbopack modifies tsconfig.json at startup

---

## Completed Updates Summary

| Category | Change | Status |

|----------|--------|--------|
| Next.js | 15.5.11 → 16.1.6 | ✅ |
| React | 19.0.0 → 19.2.4 | ✅ |
| better-auth | 1.2.0 → 1.4.18 | ✅ |
| react-query | 5.60.0 → 5.90.20 | ✅ |
| zustand | 5.0.0 → 5.0.11 | ✅ |
| lucide-react | 0.460.0 → 0.563.0 | ✅ |
| react-markdown | 9.x → streamdown 2.x | ✅ |
| middleware.ts | → proxy.ts | ✅ |
| ClickHouse | latest → 25.12.4.35-alpine | ✅ |
| MinIO | latest → RELEASE.2025-09-07 | ✅ |
| Qdrant | 1.13.2 → 1.16.2 | ✅ |

---

## Next Steps

1. [x] ~~Apply Priority 1 security fixes (Next.js, react-syntax-highlighter)~~
2. [x] ~~Pin Docker image versions (clickhouse, minio)~~
3. [x] ~~Apply Priority 2 feature updates~~
4. [x] ~~Migrate middleware.ts → proxy.ts~~
5. [x] ~~Replace react-markdown with streamdown~~
6. [ ] Test document upload after updates
7. [ ] Test chat with markdown rendering
8. [ ] Plan Tailwind v4 migration for future sprint
