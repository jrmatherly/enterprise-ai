"""SQLAlchemy database models.

Defines the core entities for the Enterprise AI Platform.
"""

from datetime import datetime
from enum import Enum as PyEnum
from typing import Optional
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all models."""
    pass


# ============================================
# Enums
# ============================================

class TenantType(str, PyEnum):
    """Tenant hierarchy types."""
    ORGANIZATION = "organization"
    DEPARTMENT = "department"
    TEAM = "team"


class KnowledgeBaseScope(str, PyEnum):
    """Knowledge base visibility scope."""
    ORGANIZATION = "organization"
    DEPARTMENT = "department"
    TEAM = "team"
    PERSONAL = "personal"


class DocumentStatus(str, PyEnum):
    """Document processing status."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class MessageRole(str, PyEnum):
    """Chat message roles."""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


# ============================================
# Core Models
# ============================================

class Tenant(Base):
    """Multi-tenant hierarchy: Org -> Dept -> Team.
    
    Each tenant can have its own rate limits, settings, and knowledge bases.
    """
    __tablename__ = "tenants"
    
    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[TenantType] = mapped_column(Enum(TenantType), nullable=False)
    parent_id: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=False), ForeignKey("tenants.id"), nullable=True)
    
    # External identity mapping (EntraID tenant/group)
    external_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, unique=True)
    
    # Rate limits (tokens per minute, requests per minute)
    tpm_limit: Mapped[int] = mapped_column(Integer, default=100000)
    rpm_limit: Mapped[int] = mapped_column(Integer, default=60)
    
    # Settings
    settings: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True, default=dict)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    parent = relationship("Tenant", remote_side=[id], backref="children")
    users = relationship("User", back_populates="tenant")
    knowledge_bases = relationship("KnowledgeBase", back_populates="tenant")
    
    __table_args__ = (
        Index("ix_tenants_parent_id", "parent_id"),
        Index("ix_tenants_external_id", "external_id"),
    )


class User(Base):
    """User identity cache from EntraID/OIDC.
    
    This is a cache of identity provider data, not the source of truth.
    """
    __tablename__ = "users"
    
    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    
    # External identity (EntraID object ID)
    external_id: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Primary tenant association
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("tenants.id"), nullable=False)
    
    # Cached roles from identity provider
    roles: Mapped[list] = mapped_column(JSONB, default=list)
    
    # Personal rate limits (override tenant defaults)
    tpm_limit: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    rpm_limit: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    tenant = relationship("Tenant", back_populates="users")
    # Note: Sessions use flexible user_id (String) to support both UUID and better-auth IDs
    documents = relationship("Document", back_populates="uploaded_by")
    
    __table_args__ = (
        Index("ix_users_external_id", "external_id"),
        Index("ix_users_email", "email"),
        Index("ix_users_tenant_id", "tenant_id"),
    )


class Session(Base):
    """Chat session / conversation thread.
    
    Each session maintains conversation history and context.
    user_id can be either a UUID (dev mode) or better-auth ID (SSO login).
    """
    __tablename__ = "sessions"
    
    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    
    # Session metadata
    title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Knowledge bases attached to this session
    knowledge_base_ids: Mapped[list] = mapped_column(JSONB, default=list)
    
    # Session state
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Usage tracking for the session
    total_tokens: Mapped[int] = mapped_column(Integer, default=0)
    total_cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    
    # Langfuse trace ID for observability
    trace_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    last_message_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    # Note: user_id is a String that can hold either UUID (dev) or better-auth ID (SSO)
    # No ForeignKey to allow flexibility with different auth providers
    messages = relationship("Message", back_populates="session", order_by="Message.created_at")
    
    __table_args__ = (
        Index("ix_sessions_user_id", "user_id"),
        Index("ix_sessions_created_at", "created_at"),
    )


class Message(Base):
    """Individual message in a chat session."""
    __tablename__ = "messages"
    
    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    session_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("sessions.id"), nullable=False)
    
    # Message content
    role: Mapped[MessageRole] = mapped_column(Enum(MessageRole), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    
    # For tool calls/responses
    tool_calls: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    tool_call_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # RAG context used for this message
    retrieved_context: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    
    # Token usage for this message
    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0)
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0)
    
    # Model used
    model: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # Langfuse span ID
    span_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    session = relationship("Session", back_populates="messages")
    
    __table_args__ = (
        Index("ix_messages_session_id", "session_id"),
        Index("ix_messages_created_at", "created_at"),
    )


# ============================================
# Knowledge Base Models
# ============================================

class KnowledgeBase(Base):
    """Knowledge base containing documents for RAG."""
    __tablename__ = "knowledge_bases"
    
    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("tenants.id"), nullable=False)
    
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Visibility scope
    scope: Mapped[KnowledgeBaseScope] = mapped_column(Enum(KnowledgeBaseScope), nullable=False)
    
    # Owner (for personal KBs)
    owner_id: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=True)
    
    # Qdrant collection name
    collection_name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    
    # Embedding model used
    embedding_model: Mapped[str] = mapped_column(String(100), default="text-embedding-3-small")
    
    # Document count cache
    document_count: Mapped[int] = mapped_column(Integer, default=0)
    
    # Sharing settings
    is_shared: Mapped[bool] = mapped_column(Boolean, default=False)
    shared_with: Mapped[list] = mapped_column(JSONB, default=list)  # List of tenant/user IDs
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    tenant = relationship("Tenant", back_populates="knowledge_bases")
    documents = relationship("Document", back_populates="knowledge_base")
    
    __table_args__ = (
        Index("ix_knowledge_bases_tenant_id", "tenant_id"),
        Index("ix_knowledge_bases_owner_id", "owner_id"),
        Index("ix_knowledge_bases_scope", "scope"),
    )


class Document(Base):
    """Document metadata for RAG.
    
    Actual content is chunked and stored in Qdrant.
    """
    __tablename__ = "documents"
    
    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    knowledge_base_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("knowledge_bases.id"), nullable=False)
    
    # Document metadata
    filename: Mapped[str] = mapped_column(String(500), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    
    # Processing status
    status: Mapped[DocumentStatus] = mapped_column(Enum(DocumentStatus), default=DocumentStatus.PENDING)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Chunking info
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    chunking_strategy: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    # Source tracking
    source_url: Mapped[Optional[str]] = mapped_column(String(2000), nullable=True)
    uploaded_by_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)
    
    # File storage location (MinIO path)
    storage_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    # Content hash for deduplication
    content_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    knowledge_base = relationship("KnowledgeBase", back_populates="documents")
    uploaded_by = relationship("User", back_populates="documents")
    
    __table_args__ = (
        Index("ix_documents_knowledge_base_id", "knowledge_base_id"),
        Index("ix_documents_status", "status"),
        Index("ix_documents_content_hash", "content_hash"),
    )


# ============================================
# Audit & Usage Models
# ============================================

class AuditLog(Base):
    """Audit trail for compliance and security."""
    __tablename__ = "audit_logs"
    
    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    
    # Who
    user_id: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=True)
    tenant_id: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=False), ForeignKey("tenants.id"), nullable=True)
    
    # What
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Details
    details: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    
    # Request context
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    # Result
    success: Mapped[bool] = mapped_column(Boolean, default=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Timestamp
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        Index("ix_audit_logs_user_id", "user_id"),
        Index("ix_audit_logs_tenant_id", "tenant_id"),
        Index("ix_audit_logs_action", "action"),
        Index("ix_audit_logs_created_at", "created_at"),
    )


class UsageRecord(Base):
    """Usage tracking for FinOps and billing."""
    __tablename__ = "usage_records"
    
    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    
    # Who
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("tenants.id"), nullable=False)
    session_id: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=False), ForeignKey("sessions.id"), nullable=True)
    
    # What
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    operation: Mapped[str] = mapped_column(String(50), nullable=False)  # chat, embedding, etc.
    
    # Usage
    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0)
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0)
    
    # Cost
    cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    
    # Performance
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    cache_hit: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Trace ID for correlation
    trace_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Timestamp
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        Index("ix_usage_records_user_id", "user_id"),
        Index("ix_usage_records_tenant_id", "tenant_id"),
        Index("ix_usage_records_model", "model"),
        Index("ix_usage_records_created_at", "created_at"),
    )
