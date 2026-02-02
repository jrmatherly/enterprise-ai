"""Application configuration using Pydantic Settings.

All configuration is loaded from environment variables.
See dev/.env.example for available settings.
"""

import json
from functools import lru_cache
from typing import Any

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore"
    )

    # ============================================
    # Application
    # ============================================
    app_name: str = "Enterprise AI Platform"
    app_version: str = "0.1.0"
    environment: str = "development"
    debug: bool = False

    # API Server
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_prefix: str = "/api/v1"
    allowed_origins: list[str] = ["http://localhost:3000", "http://localhost:8080"]

    # ============================================
    # Database (PostgreSQL)
    # ============================================
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_user: str = "postgres"
    postgres_password: str = "postgres"
    postgres_db: str = "langfuse"  # Default DB (used by Langfuse)
    postgres_app_db: str = "eai"  # Application database

    # Explicit DATABASE_URL takes precedence if set
    database_url: str | None = None

    @property
    def get_database_url(self) -> str:
        """Get database URL - explicit or constructed from components."""
        if self.database_url:
            return self.database_url
        return f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_app_db}"

    # ============================================
    # Redis
    # ============================================
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_auth: str = "redissecret"

    @property
    def redis_url(self) -> str:
        """Construct Redis URL with auth."""
        return f"redis://:{self.redis_auth}@{self.redis_host}:{self.redis_port}/0"

    # ============================================
    # Qdrant (Vector Database)
    # ============================================
    qdrant_url: str = "http://localhost:6333"
    qdrant_collection: str = "documents"
    qdrant_api_key: str | None = None

    # ============================================
    # Azure AI Foundry - Multi-Region
    # ============================================
    # Region: East US
    azure_ai_eastus_endpoint: str = ""
    azure_ai_eastus_api_key: str = ""
    azure_ai_eastus_models: str = ""  # Comma-separated: gpt-4o-mini,gpt-4o-nano

    # Region: East US 2
    azure_ai_eastus2_endpoint: str = ""
    azure_ai_eastus2_api_key: str = ""
    azure_ai_eastus2_models: str = ""  # Comma-separated

    # Model Routing (JSON: model -> region)
    azure_ai_model_routing: str = "{}"

    # Defaults
    azure_ai_default_model: str = "gpt-4o-mini"
    azure_ai_default_region: str = "eastus"
    azure_openai_api_version: str = "2025-04-01-preview"

    @field_validator("azure_ai_model_routing", mode="before")
    @classmethod
    def parse_model_routing(cls, v: Any) -> str:
        """Ensure model routing is valid JSON string."""
        if isinstance(v, dict):
            return json.dumps(v)
        return v or "{}"

    def get_model_routing(self) -> dict[str, str]:
        """Parse model routing config as dict."""
        try:
            return json.loads(self.azure_ai_model_routing)
        except json.JSONDecodeError:
            return {}

    def get_endpoint_for_model(self, model: str) -> tuple[str, str]:
        """Get endpoint and API key for a model based on routing config.

        Returns:
            Tuple of (endpoint_url, api_key)
        """
        routing = self.get_model_routing()
        region = routing.get(model, self.azure_ai_default_region)

        if region == "eastus":
            return self.azure_ai_eastus_endpoint, self.azure_ai_eastus_api_key
        if region == "eastus2":
            return self.azure_ai_eastus2_endpoint, self.azure_ai_eastus2_api_key
        # Default to eastus
        return self.azure_ai_eastus_endpoint, self.azure_ai_eastus_api_key

    # ============================================
    # Microsoft Entra ID (Authentication)
    # ============================================
    azure_tenant_id: str = ""
    azure_client_id: str = ""
    azure_client_secret: str = ""
    azure_redirect_uri: str = "http://localhost:8000/auth/callback"

    @property
    def entra_authority(self) -> str:
        """Construct Entra ID authority URL."""
        if self.azure_tenant_id:
            return f"https://login.microsoftonline.com/{self.azure_tenant_id}"
        return ""

    @property
    def entra_issuer(self) -> str:
        """Construct Entra ID issuer URL for token validation."""
        if self.azure_tenant_id:
            return f"https://login.microsoftonline.com/{self.azure_tenant_id}/v2.0"
        return ""

    # ============================================
    # Better Auth (Frontend Session Management)
    # ============================================
    better_auth_url: str = "http://localhost:3001"  # JWT issuer/audience (external)
    better_auth_internal_url: str | None = None  # Internal URL for JWKS fetch (Docker)

    # ============================================
    # Rate Limiting
    # ============================================
    rate_limit_tpm: int = 100000  # Tokens per minute
    rate_limit_rpm: int = 60  # Requests per minute

    # ============================================
    # Session Management
    # ============================================
    max_sessions_per_user: int = 50  # Maximum active sessions per user
    session_auto_cleanup: bool = True  # Auto-delete oldest sessions when limit exceeded

    # ============================================
    # Embeddings
    # ============================================
    embedding_model: str = Field(
        default="text-embedding-3-small", description="Azure OpenAI embedding model name"
    )
    embedding_dimensions: int = Field(
        default=1536, description="Embedding vector dimensions (must match model)"
    )

    # ============================================
    # Semantic Caching
    # ============================================
    semantic_cache_enabled: bool = True
    semantic_cache_threshold: float = 0.95
    semantic_cache_ttl: int = 3600

    # ============================================
    # Langfuse (v3 Observability)
    # ============================================
    langfuse_host: str = "http://localhost:3000"
    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""

    # ============================================
    # OpenTelemetry
    # ============================================
    otlp_endpoint: str = ""

    # ============================================
    # Logging
    # ============================================
    log_level: str = "INFO"
    log_format: str = "console"  # "json" or "console"

    # ============================================
    # Development Security (DANGER ZONE)
    # ============================================
    # SECURITY: Both conditions must be true for dev bypass to work:
    # 1. environment == "development"
    # 2. dev_bypass_enabled == True (explicit opt-in)
    # This prevents accidental bypass in misconfigured environments
    dev_bypass_enabled: bool = Field(
        default=False,
        description="Explicitly enable X-Dev-Bypass header. Requires environment=development.",
    )


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
