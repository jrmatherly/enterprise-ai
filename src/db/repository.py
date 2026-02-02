"""Database repository for session and message persistence.

Provides async CRUD operations for chat sessions and messages.
"""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import get_settings
from src.db.models import Message, MessageRole, Session, UsageRecord

settings = get_settings()


class SessionRepository:
    """Repository for chat session operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        user_id: str,
        title: str | None = None,
        knowledge_base_ids: list[str] | None = None,
    ) -> Session:
        """Create a new chat session."""
        session = Session(
            id=str(uuid4()),
            user_id=user_id,
            title=title,
            knowledge_base_ids=knowledge_base_ids or [],
            is_active=True,
            total_tokens=0,
            total_cost_usd=0.0,
        )
        self.db.add(session)
        await self.db.flush()
        return session

    async def get(self, session_id: str) -> Session | None:
        """Get a session by ID."""
        result = await self.db.execute(select(Session).where(Session.id == session_id))
        return result.scalar_one_or_none()

    async def get_or_create(
        self,
        session_id: str | None,
        user_id: str,
        knowledge_base_ids: list[str] | None = None,
    ) -> tuple[Session, bool]:
        """Get existing session or create new one. Returns (session, created).

        If creating a new session and the user has exceeded max_sessions_per_user,
        the oldest inactive sessions will be cleaned up automatically.
        """
        if session_id:
            session = await self.get(session_id)
            if session:
                return session, False

        # Cleanup excess sessions before creating new one
        if settings.session_auto_cleanup:
            await self._cleanup_excess_sessions(user_id, settings.max_sessions_per_user - 1)

        # Create new session
        session = await self.create(
            user_id=user_id,
            knowledge_base_ids=knowledge_base_ids,
        )
        return session, True

    async def _cleanup_excess_sessions(self, user_id: str, max_to_keep: int) -> None:
        """Delete oldest sessions if user exceeds the limit.

        Marks excess sessions as inactive (soft delete).
        """
        # Count active sessions
        count_query = select(func.count(Session.id)).where(
            Session.user_id == user_id,
            Session.is_active,
        )
        result = await self.db.execute(count_query)
        session_count = result.scalar() or 0

        if session_count > max_to_keep:
            # Get IDs of sessions to deactivate (oldest first)
            excess_count = session_count - max_to_keep
            excess_query = (
                select(Session.id)
                .where(Session.user_id == user_id, Session.is_active)
                .order_by(Session.updated_at.asc())
                .limit(excess_count)
            )
            result = await self.db.execute(excess_query)
            session_ids_to_delete = [row[0] for row in result.fetchall()]

            if session_ids_to_delete:
                # Soft delete by marking as inactive
                await self.db.execute(
                    update(Session)
                    .where(Session.id.in_(session_ids_to_delete))
                    .values(is_active=False)
                )

    async def get_user_sessions(
        self,
        user_id: str,
        limit: int = 50,
        offset: int = 0,
        active_only: bool = True,
    ) -> list[Session]:
        """Get sessions for a user, ordered by most recent activity."""
        query = select(Session).where(Session.user_id == user_id)

        if active_only:
            query = query.where(Session.is_active)

        query = query.order_by(Session.updated_at.desc())
        query = query.limit(limit).offset(offset)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def update_usage(
        self,
        session_id: str,
        tokens: int,
        cost_usd: float = 0.0,
    ) -> None:
        """Update session usage stats."""
        await self.db.execute(
            update(Session)
            .where(Session.id == session_id)
            .values(
                total_tokens=Session.total_tokens + tokens,
                total_cost_usd=Session.total_cost_usd + cost_usd,
                last_message_at=func.now(),
                updated_at=func.now(),
            )
        )

    async def set_title(self, session_id: str, title: str) -> None:
        """Set the session title."""
        await self.db.execute(
            update(Session)
            .where(Session.id == session_id)
            .values(title=title, updated_at=func.now())
        )

    async def archive(self, session_id: str) -> None:
        """Archive a session (soft delete)."""
        await self.db.execute(
            update(Session)
            .where(Session.id == session_id)
            .values(is_active=False, updated_at=func.now())
        )


class MessageRepository:
    """Repository for chat message operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        session_id: str,
        role: MessageRole,
        content: str,
        model: str | None = None,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        tool_calls: list | None = None,
        tool_call_id: str | None = None,
        retrieved_context: list | None = None,
        span_id: str | None = None,
    ) -> Message:
        """Create a new message in a session."""
        message = Message(
            id=str(uuid4()),
            session_id=session_id,
            role=role,
            content=content,
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            tool_calls=tool_calls,
            tool_call_id=tool_call_id,
            retrieved_context=retrieved_context,
            span_id=span_id,
        )
        self.db.add(message)
        await self.db.flush()
        return message

    async def get(self, message_id: str) -> Message | None:
        """Get a message by ID."""
        result = await self.db.execute(select(Message).where(Message.id == message_id))
        return result.scalar_one_or_none()

    async def get_session_messages(
        self,
        session_id: str,
        limit: int = 100,
        before_id: str | None = None,
    ) -> list[Message]:
        """Get messages for a session, ordered chronologically."""
        query = select(Message).where(Message.session_id == session_id)

        if before_id:
            # Get messages before a specific message (for pagination)
            subq = select(Message.created_at).where(Message.id == before_id).scalar_subquery()
            query = query.where(Message.created_at < subq)

        query = query.order_by(Message.created_at.asc())
        query = query.limit(limit)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_recent_messages(
        self,
        session_id: str,
        limit: int = 20,
    ) -> list[Message]:
        """Get the most recent messages for context window."""
        query = (
            select(Message)
            .where(Message.session_id == session_id)
            .order_by(Message.created_at.desc())
            .limit(limit)
        )
        result = await self.db.execute(query)
        # Reverse to get chronological order
        messages = list(result.scalars().all())
        return list(reversed(messages))

    async def count_session_messages(self, session_id: str) -> int:
        """Count messages in a session."""
        result = await self.db.execute(
            select(func.count(Message.id)).where(Message.session_id == session_id)
        )
        return result.scalar() or 0


class UsageRepository:
    """Repository for usage tracking (FinOps)."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def record(
        self,
        user_id: str,
        tenant_id: str,
        model: str,
        operation: str,
        prompt_tokens: int,
        completion_tokens: int,
        cost_usd: float = 0.0,
        latency_ms: int = 0,
        cache_hit: bool = False,
        session_id: str | None = None,
        trace_id: str | None = None,
    ) -> UsageRecord:
        """Record a usage event."""
        record = UsageRecord(
            id=str(uuid4()),
            user_id=user_id,
            tenant_id=tenant_id,
            session_id=session_id,
            model=model,
            operation=operation,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            cost_usd=cost_usd,
            latency_ms=latency_ms,
            cache_hit=cache_hit,
            trace_id=trace_id,
        )
        self.db.add(record)
        await self.db.flush()
        return record

    async def get_user_usage(
        self,
        user_id: str,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> dict:
        """Get aggregated usage stats for a user."""
        query = select(
            func.sum(UsageRecord.total_tokens).label("total_tokens"),
            func.sum(UsageRecord.cost_usd).label("total_cost"),
            func.count(UsageRecord.id).label("request_count"),
        ).where(UsageRecord.user_id == user_id)

        if start_date:
            query = query.where(UsageRecord.created_at >= start_date)
        if end_date:
            query = query.where(UsageRecord.created_at <= end_date)

        result = await self.db.execute(query)
        row = result.one()

        return {
            "total_tokens": row.total_tokens or 0,
            "total_cost_usd": float(row.total_cost or 0),
            "request_count": row.request_count or 0,
        }

    async def get_tenant_usage(
        self,
        tenant_id: str,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> dict:
        """Get aggregated usage stats for a tenant."""
        query = select(
            func.sum(UsageRecord.total_tokens).label("total_tokens"),
            func.sum(UsageRecord.cost_usd).label("total_cost"),
            func.count(UsageRecord.id).label("request_count"),
        ).where(UsageRecord.tenant_id == tenant_id)

        if start_date:
            query = query.where(UsageRecord.created_at >= start_date)
        if end_date:
            query = query.where(UsageRecord.created_at <= end_date)

        result = await self.db.execute(query)
        row = result.one()

        return {
            "total_tokens": row.total_tokens or 0,
            "total_cost_usd": float(row.total_cost or 0),
            "request_count": row.request_count or 0,
        }
