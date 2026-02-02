"""FastAPI application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import make_asgi_app

from src.agent.runtime import shutdown_runtime
from src.api.routes import chat, health, knowledge, sessions
from src.auth.middleware import AuthMiddleware
from src.core.config import get_settings
from src.db.database import close_db, init_db

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan - startup and shutdown."""
    # Startup
    print(f"Starting {settings.app_name} v{settings.app_version}")
    print(f"Environment: {settings.environment}")

    # Initialize database (create tables if not exists)
    # In production, use Alembic migrations instead
    if settings.environment == "development":
        try:
            await init_db()
            print("Database initialized")
        except Exception as e:
            print(f"Database initialization skipped: {e}")

    # Mark startup complete for health checks
    health.set_startup_complete()
    print("Startup complete - ready to accept requests")

    yield

    # Shutdown
    print("Shutting down...")
    await shutdown_runtime()
    await close_db()
    print("Shutdown complete")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Enterprise AI Adoption Platform API",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    lifespan=lifespan,
)

# Auth middleware (validates JWTs, sets request.state.user)
app.add_middleware(AuthMiddleware)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# TODO: Add rate limiting middleware
# TODO: Add request logging middleware

# Health check routes (no auth required - public paths)
app.include_router(health.router, tags=["Health"])

# API routes (auth required)
app.include_router(chat.router, prefix=settings.api_prefix, tags=["Chat"])
app.include_router(knowledge.router, prefix=settings.api_prefix, tags=["Knowledge Base"])
app.include_router(sessions.router, prefix=settings.api_prefix, tags=["Sessions"])

# Prometheus metrics endpoint
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)


@app.get("/")
async def root():
    """Root endpoint with API info."""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs" if settings.debug else None,
        "health": "/health/ready",
    }
