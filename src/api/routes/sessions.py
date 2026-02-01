"""Session management endpoints."""

from datetime import datetime
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from src.api.deps import CurrentUser, DB
from src.db.models import Session, Message


router = APIRouter()


class SessionResponse(BaseModel):
    """Session summary."""
    id: str
    title: Optional[str]
    message_count: int
    total_tokens: int
    created_at: str
    updated_at: str
    last_message_at: Optional[str]


class SessionDetailResponse(SessionResponse):
    """Session with message history."""
    messages: list[dict]


class CreateSessionRequest(BaseModel):
    """Request to create a new session."""
    title: Optional[str] = Field(None, max_length=255)
    knowledge_base_ids: list[str] = Field(default_factory=list)


class UpdateSessionRequest(BaseModel):
    """Request to update a session."""
    title: Optional[str] = Field(None, max_length=255)


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
        query = (
            select(Session)
            .where(Session.user_id == user.sub)
            .where(Session.is_active == True)
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
                created_at=s.created_at.isoformat() + "Z",
                updated_at=s.updated_at.isoformat() + "Z",
                last_message_at=s.last_message_at.isoformat() + "Z" if s.last_message_at else None,
            )
            for s in sessions
        ]
    except Exception:
        # Database not initialized or no sessions
        return []


@router.post("/sessions", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(
    body: CreateSessionRequest,
    user: CurrentUser,
    db: DB,
):
    """Create a new chat session."""
    session = Session(
        id=str(uuid4()),
        user_id=user.sub,
        title=body.title,
        knowledge_base_ids=body.knowledge_base_ids,
    )
    
    try:
        db.add(session)
        await db.commit()
        await db.refresh(session)
        
        return SessionResponse(
            id=session.id,
            title=session.title,
            message_count=0,
            total_tokens=0,
            created_at=session.created_at.isoformat() + "Z",
            updated_at=session.updated_at.isoformat() + "Z",
            last_message_at=None,
        )
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create session: {str(e)}"
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
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found"
            )
        
        messages = []
        if include_messages and session.messages:
            messages = [
                {
                    "id": m.id,
                    "role": m.role.value,
                    "content": m.content,
                    "created_at": m.created_at.isoformat() + "Z",
                }
                for m in session.messages
            ]
        
        return SessionDetailResponse(
            id=session.id,
            title=session.title,
            message_count=len(messages),
            total_tokens=session.total_tokens,
            created_at=session.created_at.isoformat() + "Z",
            updated_at=session.updated_at.isoformat() + "Z",
            last_message_at=session.last_message_at.isoformat() + "Z" if session.last_message_at else None,
            messages=messages,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve session: {str(e)}"
        )


@router.patch("/sessions/{session_id}", response_model=SessionResponse)
async def update_session(
    session_id: str,
    body: UpdateSessionRequest,
    user: CurrentUser,
    db: DB,
):
    """Update a session's metadata."""
    try:
        query = select(Session).where(
            Session.id == session_id,
            Session.user_id == user.sub,
        )
        
        result = await db.execute(query)
        session = result.scalar_one_or_none()
        
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found"
            )
        
        if body.title is not None:
            session.title = body.title
        
        await db.commit()
        await db.refresh(session)
        
        return SessionResponse(
            id=session.id,
            title=session.title,
            message_count=len(session.messages) if session.messages else 0,
            total_tokens=session.total_tokens,
            created_at=session.created_at.isoformat() + "Z",
            updated_at=session.updated_at.isoformat() + "Z",
            last_message_at=session.last_message_at.isoformat() + "Z" if session.last_message_at else None,
        )
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update session: {str(e)}"
        )


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
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found"
            )
        
        session.is_active = False
        await db.commit()
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete session: {str(e)}"
        )
