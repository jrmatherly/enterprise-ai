# Frontend Architecture — Enterprise AI Platform

**Created:** 2026-02-01  
**Status:** Design Phase

---

## Overview

A modern React-based web UI for the Enterprise AI Platform that provides:
- Chat interface with streaming responses
- EntraID/OIDC authentication
- Session/conversation management
- Knowledge base browsing and document upload
- Admin dashboards (usage, rate limits, audit logs)

---

## Technology Stack

### Core Framework
| Technology | Purpose | Rationale |
|------------|---------|-----------|
| **Next.js 15** | React framework | SSR, App Router, API routes, excellent DX |
| **TypeScript** | Type safety | Enterprise requirement, better maintainability |
| **React 19** | UI library | Industry standard, large ecosystem |

### Styling & Components
| Technology | Purpose | Rationale |
|------------|---------|-----------|
| **Tailwind CSS** | Utility-first CSS | Rapid development, consistent design |
| **shadcn/ui** | Component library | Radix primitives, accessible, customizable |
| **Lucide Icons** | Icon library | Clean, consistent iconography |

### State & Data
| Technology | Purpose | Rationale |
|------------|---------|-----------|
| **TanStack Query** | Server state | Caching, refetching, optimistic updates |
| **Zustand** | Client state | Simple, lightweight, TypeScript-first |
| **next-auth** | Authentication | OIDC/EntraID support, session management |

### Developer Experience
| Technology | Purpose | Rationale |
|------------|---------|-----------|
| **ESLint + Prettier** | Code quality | Consistent formatting |
| **Vitest** | Testing | Fast, Vite-compatible |
| **Playwright** | E2E testing | Cross-browser, reliable |

---

## Project Structure

```
frontend/
├── src/
│   ├── app/                      # Next.js App Router
│   │   ├── (auth)/               # Auth-required routes (grouped)
│   │   │   ├── chat/             # Chat interface
│   │   │   │   ├── page.tsx      # Main chat page
│   │   │   │   └── [sessionId]/  # Session-specific chat
│   │   │   │       └── page.tsx
│   │   │   ├── knowledge/        # Knowledge base management
│   │   │   │   ├── page.tsx      # List knowledge bases
│   │   │   │   └── [id]/         # Knowledge base details
│   │   │   │       └── page.tsx
│   │   │   ├── sessions/         # Session history
│   │   │   │   └── page.tsx
│   │   │   └── settings/         # User settings
│   │   │       └── page.tsx
│   │   ├── (admin)/              # Admin routes (role-protected)
│   │   │   ├── users/            # User management
│   │   │   ├── usage/            # Usage analytics
│   │   │   └── audit/            # Audit logs
│   │   ├── api/                  # API routes (BFF pattern)
│   │   │   └── auth/             # NextAuth handlers
│   │   │       └── [...nextauth]/
│   │   ├── login/                # Login page
│   │   │   └── page.tsx
│   │   ├── layout.tsx            # Root layout
│   │   ├── page.tsx              # Landing/redirect
│   │   └── globals.css           # Global styles
│   │
│   ├── components/               # Reusable components
│   │   ├── ui/                   # shadcn/ui components
│   │   │   ├── button.tsx
│   │   │   ├── input.tsx
│   │   │   ├── dialog.tsx
│   │   │   └── ...
│   │   ├── chat/                 # Chat-specific components
│   │   │   ├── ChatInterface.tsx
│   │   │   ├── MessageBubble.tsx
│   │   │   ├── MessageInput.tsx
│   │   │   ├── StreamingMessage.tsx
│   │   │   └── SourceCitation.tsx
│   │   ├── knowledge/            # Knowledge base components
│   │   │   ├── KnowledgeBaseCard.tsx
│   │   │   ├── DocumentUploader.tsx
│   │   │   └── DocumentList.tsx
│   │   ├── layout/               # Layout components
│   │   │   ├── Sidebar.tsx
│   │   │   ├── Header.tsx
│   │   │   ├── UserMenu.tsx
│   │   │   └── ThemeToggle.tsx
│   │   └── shared/               # Shared components
│   │       ├── LoadingSpinner.tsx
│   │       ├── ErrorBoundary.tsx
│   │       └── EmptyState.tsx
│   │
│   ├── lib/                      # Utilities and configurations
│   │   ├── api/                  # API client
│   │   │   ├── client.ts         # Fetch wrapper with auth
│   │   │   ├── chat.ts           # Chat API functions
│   │   │   ├── knowledge.ts      # Knowledge base API
│   │   │   └── sessions.ts       # Session API
│   │   ├── auth/                 # Auth utilities
│   │   │   ├── config.ts         # NextAuth config
│   │   │   └── middleware.ts     # Auth middleware
│   │   ├── hooks/                # Custom React hooks
│   │   │   ├── useChat.ts        # Chat with streaming
│   │   │   ├── useSession.ts     # Session management
│   │   │   └── useRateLimit.ts   # Rate limit display
│   │   └── utils/                # General utilities
│   │       ├── cn.ts             # Class name helper
│   │       └── format.ts         # Formatters
│   │
│   ├── stores/                   # Zustand stores
│   │   ├── chatStore.ts          # Chat state
│   │   └── uiStore.ts            # UI preferences
│   │
│   └── types/                    # TypeScript types
│       ├── api.ts                # API response types
│       ├── chat.ts               # Chat types
│       └── user.ts               # User types
│
├── public/                       # Static assets
│   ├── logo.svg
│   └── favicon.ico
│
├── tests/                        # Test files
│   ├── unit/
│   └── e2e/
│
├── .env.example                  # Environment template
├── .env.local                    # Local environment (not in git)
├── next.config.ts                # Next.js configuration
├── tailwind.config.ts            # Tailwind configuration
├── tsconfig.json                 # TypeScript configuration
├── package.json
└── README.md
```

---

## Key Features

### 1. Chat Interface

**Main Chat View:**
```
┌─────────────────────────────────────────────────────────────────┐
│  ☰  Enterprise AI                              [Usage] [👤 User] │
├──────────────┬──────────────────────────────────────────────────┤
│              │                                                   │
│  Sessions    │   ┌──────────────────────────────────────────┐   │
│              │   │ 🤖 How can I help you today?             │   │
│  + New Chat  │   └──────────────────────────────────────────┘   │
│              │                                                   │
│  ─────────── │   ┌──────────────────────────────────────────┐   │
│              │   │ 👤 What's our Q3 revenue target?         │   │
│  Today       │   └──────────────────────────────────────────┘   │
│  • Q3 Targe..│                                                   │
│  • Budget ...|   ┌──────────────────────────────────────────┐   │
│              │   │ 🤖 Based on the Finance KB, your Q3      │   │
│  Yesterday   │   │ revenue target is $4.2M, which is...     │   │
│  • Policy ...|   │                                          │   │
│  • HR Ques...|   │ 📎 Sources:                              │   │
│              │   │   • Q3-Targets.xlsx (Finance KB)         │   │
│              │   │   • Revenue-Plan.pdf (Finance KB)        │   │
│              │   └──────────────────────────────────────────┘   │
│              │                                                   │
│              │   ┌──────────────────────────────────────────┐   │
│              │   │ Type a message...          [📎] [Send ➤] │   │
│              │   └──────────────────────────────────────────┘   │
│              │                                                   │
│  ─────────── │   Knowledge Bases: [Finance ▼] [HR ▼] [+]        │
│  [⚙ Settings]│                                                   │
└──────────────┴──────────────────────────────────────────────────┘
```

**Features:**
- Streaming responses with typing indicator
- Markdown rendering in messages
- Code syntax highlighting
- Source citations with links
- Knowledge base selection
- Session persistence and history
- Mobile-responsive design

### 2. Authentication Flow

```
User visits /chat
    │
    ▼
┌─────────────────┐     No      ┌─────────────────┐
│ Has valid       │ ─────────►  │ Redirect to     │
│ session?        │             │ /login          │
└─────────────────┘             └─────────────────┘
    │ Yes                              │
    ▼                                  ▼
┌─────────────────┐             ┌─────────────────┐
│ Load chat       │             │ "Sign in with   │
│ interface       │             │  Microsoft"     │
└─────────────────┘             └─────────────────┘
                                       │
                                       ▼
                                ┌─────────────────┐
                                │ EntraID OAuth   │
                                │ flow            │
                                └─────────────────┘
                                       │
                                       ▼
                                ┌─────────────────┐
                                │ Callback with   │
                                │ tokens          │
                                └─────────────────┘
                                       │
                                       ▼
                                ┌─────────────────┐
                                │ Create session, │
                                │ redirect /chat  │
                                └─────────────────┘
```

### 3. Knowledge Base Management

**List View:**
- Grid/list of accessible knowledge bases
- Scope badges (Org, Dept, Team, Personal)
- Document count and last updated
- Quick search/filter

**Detail View:**
- Document list with metadata
- Upload interface (drag & drop)
- Processing status indicators
- Delete/manage documents

### 4. Admin Dashboard

**Usage Analytics:**
- Token consumption over time
- Per-user/per-tenant breakdown
- Cost estimation
- Rate limit status

**Audit Logs:**
- Searchable log viewer
- Filter by action, user, resource
- Export capability

---

## API Integration

### Backend Endpoints Used

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/v1/chat` | POST | Send message, get response |
| `/api/v1/chat/stream` | POST | Streaming chat response |
| `/api/v1/usage` | GET | Rate limit status |
| `/api/v1/sessions` | GET | List user sessions |
| `/api/v1/sessions/{id}` | GET | Get session with messages |
| `/api/v1/sessions/{id}` | DELETE | Archive session |
| `/api/v1/knowledge-bases` | GET | List knowledge bases |
| `/api/v1/knowledge-bases/{id}/documents` | GET/POST | Documents |
| `/health/ready` | GET | Health check |

### API Client Pattern

```typescript
// lib/api/client.ts
import { getSession } from 'next-auth/react';

const API_BASE = process.env.NEXT_PUBLIC_API_URL;

export async function apiClient<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const session = await getSession();
  
  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(session?.accessToken && {
        Authorization: `Bearer ${session.accessToken}`,
      }),
      ...options.headers,
    },
  });

  if (!response.ok) {
    throw new APIError(response.status, await response.json());
  }

  return response.json();
}
```

### Streaming Chat Hook

```typescript
// lib/hooks/useChat.ts
export function useChat(sessionId?: string) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);

  const sendMessage = useCallback(async (content: string) => {
    // Add user message optimistically
    const userMessage = { role: 'user', content };
    setMessages(prev => [...prev, userMessage]);
    setIsStreaming(true);

    try {
      const response = await fetch('/api/v1/chat/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: content, session_id: sessionId }),
      });

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();
      let assistantMessage = '';

      while (true) {
        const { done, value } = await reader!.read();
        if (done) break;

        const chunk = decoder.decode(value);
        const lines = chunk.split('\n');
        
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = JSON.parse(line.slice(6));
            if (data.content) {
              assistantMessage += data.content;
              setMessages(prev => [
                ...prev.slice(0, -1),
                { role: 'assistant', content: assistantMessage },
              ]);
            }
          }
        }
      }
    } finally {
      setIsStreaming(false);
    }
  }, [sessionId]);

  return { messages, sendMessage, isStreaming };
}
```

---

## Environment Variables

```bash
# .env.local

# API Backend
NEXT_PUBLIC_API_URL=http://localhost:8000

# Authentication (EntraID)
AZURE_AD_CLIENT_ID=your-client-id
AZURE_AD_CLIENT_SECRET=your-client-secret
AZURE_AD_TENANT_ID=your-tenant-id
NEXTAUTH_URL=http://localhost:3001
NEXTAUTH_SECRET=generate-a-secret

# Feature Flags
NEXT_PUBLIC_ENABLE_ADMIN=true
NEXT_PUBLIC_ENABLE_KNOWLEDGE_BASES=true
```

---

## Development Workflow

### Setup
```bash
cd frontend
npm install
cp .env.example .env.local
# Edit .env.local with your values
npm run dev
```

### Scripts
```bash
npm run dev          # Start dev server (port 3001)
npm run build        # Production build
npm run start        # Start production server
npm run lint         # Run ESLint
npm run test         # Run unit tests
npm run test:e2e     # Run E2E tests
npm run typecheck    # TypeScript check
```

### mise Integration
```toml
# Added to root mise.toml
[tasks.ui]
description = "Start frontend dev server"
run = "cd frontend && npm run dev"

[tasks.ui-build]
description = "Build frontend for production"
run = "cd frontend && npm run build"
```

---

## Design System

### Colors (Dark/Light Mode)

```css
/* Semantic colors mapped to Tailwind */
--background: hsl(0 0% 100%);        /* Light: white */
--foreground: hsl(222 84% 5%);       /* Light: near-black */
--primary: hsl(221 83% 53%);         /* Brand blue */
--secondary: hsl(210 40% 96%);       /* Light gray */
--accent: hsl(262 83% 58%);          /* Purple accent */
--destructive: hsl(0 84% 60%);       /* Red for errors */
--muted: hsl(210 40% 96%);           /* Muted backgrounds */
--border: hsl(214 32% 91%);          /* Border color */
```

### Typography
- **Font:** Inter (system font fallback)
- **Headings:** Semi-bold, tight letter-spacing
- **Body:** Regular, relaxed line-height
- **Code:** JetBrains Mono / system monospace

### Spacing Scale
Using Tailwind's default scale (4px base):
- `p-2` (8px), `p-4` (16px), `p-6` (24px), `p-8` (32px)

### Component Patterns
- Cards with subtle shadows
- Rounded corners (8px default)
- Accessible focus states
- Smooth transitions (150ms)

---

## Security Considerations

1. **Authentication:**
   - All routes except `/login` require authentication
   - JWT tokens stored in HTTP-only cookies
   - CSRF protection via NextAuth

2. **API Calls:**
   - All API calls include auth headers
   - Token refresh handled automatically
   - Rate limit errors handled gracefully

3. **Content Security:**
   - Markdown sanitized before rendering
   - XSS protection via React
   - CSP headers configured

4. **Data Handling:**
   - No sensitive data in localStorage
   - Session data encrypted
   - Audit logging for admin actions

---

## Deployment

### Docker
```dockerfile
FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV production
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public
EXPOSE 3000
CMD ["node", "server.js"]
```

### Kubernetes
- Deployment with 2+ replicas
- Service + Ingress
- ConfigMap for environment
- HPA for auto-scaling

---

## Implementation Phases

### Phase 1: Foundation (This Sprint)
- [x] Project setup (Next.js, Tailwind, shadcn/ui)
- [ ] Authentication with EntraID
- [ ] Basic chat interface
- [ ] Streaming message support
- [ ] Session sidebar

### Phase 2: Knowledge Bases
- [ ] Knowledge base list view
- [ ] Document upload
- [ ] Knowledge base selector in chat

### Phase 3: Admin Features
- [ ] Usage dashboard
- [ ] Audit log viewer
- [ ] User management

### Phase 4: Polish
- [ ] Dark mode
- [ ] Mobile responsive
- [ ] Keyboard shortcuts
- [ ] Accessibility audit

---

*This document is the source of truth for frontend architecture decisions.*
