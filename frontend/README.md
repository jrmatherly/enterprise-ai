# Enterprise AI Platform — Frontend

Modern React-based web UI for the Enterprise AI Platform.

## Tech Stack

- **Next.js 15** — React framework with App Router
- **TypeScript** — Type safety
- **Tailwind CSS** — Styling
- **TanStack Query** — Server state management
- **Zustand** — Client state management

## Quick Start

```bash
# Install dependencies
npm install

# Copy environment file
cp .env.example .env.local

# Start dev server (port 3001)
npm run dev
```

Make sure the backend API is running on port 8000.

## Project Structure

```
src/
├── app/                    # Next.js App Router
│   ├── layout.tsx          # Root layout
│   ├── page.tsx            # Main page
│   ├── providers.tsx       # React Query provider
│   └── globals.css         # Global styles
├── components/
│   ├── chat/               # Chat components
│   │   ├── ChatLayout.tsx
│   │   ├── ChatInterface.tsx
│   │   ├── MessageBubble.tsx
│   │   ├── MessageInput.tsx
│   │   └── SessionList.tsx
│   └── ui/                 # Reusable UI components
├── lib/
│   ├── api/                # API client
│   ├── hooks/              # Custom hooks
│   └── utils/              # Utilities
└── types/                  # TypeScript types
```

## Scripts

```bash
npm run dev       # Start dev server
npm run build     # Production build
npm run start     # Start production server
npm run lint      # Run ESLint
npm run typecheck # TypeScript check
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `NEXT_PUBLIC_API_URL` | Backend API URL | `http://localhost:8000` |

## Features

- ✅ Chat interface with streaming responses
- ✅ Message history display
- ✅ Session sidebar
- ✅ Markdown rendering
- ✅ Code syntax highlighting
- ✅ Dark/light mode support (via CSS)
- ⏳ EntraID authentication
- ⏳ Knowledge base browser
- ⏳ Admin dashboard

## Development

### Running with Backend

1. Start the backend: `mise run dev` (from project root)
2. Start the frontend: `mise run ui` (from project root)

Or from the frontend directory:
```bash
npm run dev
```

### API Proxy

The Next.js config includes a rewrite rule that proxies `/api/v1/*` requests to the backend. This avoids CORS issues during development.

## Architecture

See [docs/FRONTEND-ARCHITECTURE.md](../docs/FRONTEND-ARCHITECTURE.md) for detailed architecture documentation.
