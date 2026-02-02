"""Session management endpoints."""

from datetime import datetime
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from src.api.deps import DB, CurrentUser
from src.core.config import get_settings
from src.db.models import Session

router = APIRouter()
settings = get_settings()


def format_datetime(dt: datetime | None) -> str | None:
    """Format datetime to ISO format with Z suffix for UTC."""
    if dt is None:
        return None
    # Replace +00:00 with Z for cleaner ISO format
    return dt.isoformat().replace("+00:00", "Z")


class SessionResponse(BaseModel):
    """Session summary."""

    id: str
    title: str | None
    message_count: int
    total_tokens: int
    created_at: str
    updated_at: str
    last_message_at: str | None


class SessionDetailResponse(SessionResponse):
    """Session with message history."""

    messages: list[dict]


class CreateSessionRequest(BaseModel):
    """Request to create a new session."""

    title: str | None = Field(None, max_length=255)
    knowledge_base_ids: list[str] = Field(default_factory=list)


class UpdateSessionRequest(BaseModel):
    """Request to update a session."""

    title: str | None = Field(None, max_length=255)


@router.get("/sessions", response_model=list[SessionResponse])
async def list_sessions(
    user: CurrentUser,
    db: DB,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """List the current user's chat sessions.

    Returns sessions ordered by most recently updated.
    """
    # Note: In dev mode without real users, we'd need to handle this differently
    # For now, return empty list if no DB entries
    try:
        # Use selectinload to eagerly fetch messages to avoid lazy loading issues
        from sqlalchemy.orm import selectinload

        query = (
            select(Session)
            .options(selectinload(Session.messages))
            .where(Session.user_id == user.sub)
            .where(Session.is_active)
            .order_by(Session.updated_at.desc())
            .limit(limit)
            .offset(offset)
        )

        result = await db.execute(query)
        sessions = result.scalars().all()

        return [
            SessionResponse(
                id=s.id,
                title=s.title,
                message_count=len(s.messages) if s.messages else 0,
                total_tokens=s.total_tokens,
                created_at=format_datetime(s.created_at),
                updated_at=format_datetime(s.updated_at),
                last_message_at=format_datetime(s.last_message_at),
            )
            for s in sessions
        ]
    except Exception as e:
        # Log the error for debugging
        print(f"Error listing sessions: {e}")
        return []


@router.post("/sessions", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(
    body: CreateSessionRequest,
    user: CurrentUser,
    db: DB,
):
    """Create a new chat session.

    If the user has reached the maximum session limit, the oldest sessions
    will be automatically deleted to make room (if auto-cleanup is enabled).
    """
    try:
        # Check current session count and cleanup if needed
        if settings.session_auto_cleanup:
            await _cleanup_excess_sessions(db, user.sub, settings.max_sessions_per_user - 1)

        session = Session(
            id=str(uuid4()),
            user_id=user.sub,
            title=body.title,
            knowledge_base_ids=body.knowledge_base_ids,
        )

        db.add(session)
        await db.commit()
        await db.refresh(session)

        return SessionResponse(
            id=session.id,
            title=session.title,
            message_count=0,
            total_tokens=0,
            created_at=format_datetime(session.created_at),
            updated_at=format_datetime(session.updated_at),
            last_message_at=None,
        )
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create session: {e!s}",
        ) from None


async def _cleanup_excess_sessions(db: DB, user_id: str, max_to_keep: int):
    """Delete oldest sessions if user exceeds the limit.

    Marks excess sessions as inactive (soft delete).
    """
    # Count active sessions
    count_query = select(func.count(Session.id)).where(
        Session.user_id == user_id,
        Session.is_active,
    )
    result = await db.execute(count_query)
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
        result = await db.execute(excess_query)
        session_ids_to_delete = [row[0] for row in result.fetchall()]

        if session_ids_to_delete:
            # Soft delete by marking as inactive
            from sqlalchemy import update

            await db.execute(
                update(Session).where(Session.id.in_(session_ids_to_delete)).values(is_active=False)
            )


@router.get("/sessions/{session_id}", response_model=SessionDetailResponse)
async def get_session(
    session_id: str,
    user: CurrentUser,
    db: DB,
    include_messages: bool = Query(True),
):
    """Get a session by ID with optional message history."""
    try:
        query = select(Session).where(
            Session.id == session_id,
            Session.user_id == user.sub,
        )

        if include_messages:
            query = query.options(selectinload(Session.messages))

        result = await db.execute(query)
        session = result.scalar_one_or_none()

        if not session:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

        messages = []
        if include_messages and session.messages:
            messages = [
                {
                    "id": m.id,
                    "role": m.role.value,
                    "content": m.content,
                    "created_at": format_datetime(m.created_at),
                }
                for m in session.messages
            ]

        return SessionDetailResponse(
            id=session.id,
            title=session.title,
            message_count=len(messages),
            total_tokens=session.total_tokens,
            created_at=format_datetime(session.created_at),
            updated_at=format_datetime(session.updated_at),
            last_message_at=format_datetime(session.last_message_at),
            messages=messages,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve session: {e!s}",
        ) from None


@router.patch("/sessions/{session_id}", response_model=SessionResponse)
async def update_session(
    session_id: str,
    body: UpdateSessionRequest,
    user: CurrentUser,
    db: DB,
):
    """Update a session's metadata."""
    try:
        query = (
            select(Session)
            .options(selectinload(Session.messages))
            .where(Session.id == session_id, Session.user_id == user.sub)
        )

        result = await db.execute(query)
        session = result.scalar_one_or_none()

        if not session:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

        if body.title is not None:
            session.title = body.title

        await db.commit()
        await db.refresh(session)

        return SessionResponse(
            id=session.id,
            title=session.title,
            message_count=len(session.messages) if session.messages else 0,
            total_tokens=session.total_tokens,
            created_at=format_datetime(session.created_at),
            updated_at=format_datetime(session.updated_at),
            last_message_at=format_datetime(session.last_message_at),
        )
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update session: {e!s}",
        ) from None


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(
    session_id: str,
    user: CurrentUser,
    db: DB,
):
    """Soft delete a session (marks as inactive)."""
    try:
        query = select(Session).where(
            Session.id == session_id,
            Session.user_id == user.sub,
        )

        result = await db.execute(query)
        session = result.scalar_one_or_none()

        if not session:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

        session.is_active = False
        await db.commit()

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete session: {e!s}",
        ) from None
