"""Chat/agent interaction endpoints."""

import json
from datetime import datetime
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from src.api.deps import (
    CurrentUser, Runtime, DB, RateLimiter,
    SessionRepo, MessageRepo, UsageRepo,
)
from src.agent.runtime import ChatMessage, ChatContext
from src.core.rate_limiting import RateLimitExceeded
from src.db.models import MessageRole


router = APIRouter()


class ChatMessageInput(BaseModel):
    """A single chat message for input."""
    role: str = Field(..., description="Message role: user, assistant, or system")
    content: str = Field(..., description="Message content")


class ChatRequest(BaseModel):
    """Chat completion request."""
    message: str = Field(..., description="User message", max_length=32000)
    session_id: Optional[str] = Field(None, description="Session ID for conversation continuity")
    stream: bool = Field(False, description="Whether to stream the response")
    knowledge_base_ids: Optional[list[str]] = Field(
        None, 
        description="Knowledge base IDs to search for context"
    )
    model: Optional[str] = Field(None, description="Model to use (uses default if not specified)")
    temperature: float = Field(0.7, ge=0.0, le=2.0, description="Sampling temperature")
    max_tokens: int = Field(4096, ge=1, le=128000, description="Maximum tokens in response")
    history: Optional[list[ChatMessageInput]] = Field(
        None,
        description="Previous conversation messages (overrides stored history)"
    )


class ChatResponse(BaseModel):
    """Chat completion response."""
    session_id: str
    message_id: str
    content: str
    model: str
    sources: Optional[list[dict]] = None
    usage: dict
    latency_ms: float
    created_at: str


class UsageInfo(BaseModel):
    """Rate limit usage information."""
    tokens: dict
    requests: dict


@router.get("/usage", response_model=UsageInfo)
async def get_usage(
    user: CurrentUser,
    rate_limiter: RateLimiter,
):
    """Get current rate limit usage for the authenticated user's tenant."""
    usage = await rate_limiter.get_usage(user.tenant_id)
    return usage


@router.post("/chat", response_model=ChatResponse)
async def chat(
    body: ChatRequest,
    user: CurrentUser,
    runtime: Runtime,
    db: DB,
    rate_limiter: RateLimiter,
    session_repo: SessionRepo,
    message_repo: MessageRepo,
    usage_repo: UsageRepo,
):
    """Send a message and get a response from the AI agent.
    
    The agent will:
    1. Check rate limits (TPM and RPM)
    2. Search relevant knowledge bases for context (if specified)
    3. Generate a response using Azure AI Foundry
    4. Store the conversation in the database
    5. Include source citations when using retrieved context
    
    Rate limits apply based on your tenant's configuration.
    """
    message_id = str(uuid4())
    trace_id = str(uuid4())
    
    # Check rate limits
    try:
        await rate_limiter.check_request_limit(user.tenant_id)
    except RateLimitExceeded as e:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=str(e),
            headers={
                "Retry-After": str(e.retry_after),
                "X-RateLimit-Limit": str(e.limit),
                "X-RateLimit-Remaining": str(e.remaining),
            },
        )
    
    # Get or create session
    session, created = await session_repo.get_or_create(
        session_id=body.session_id,
        user_id=user.sub,
        knowledge_base_ids=body.knowledge_base_ids,
    )
    
    # Build context
    context = ChatContext(
        user_id=user.sub,
        tenant_id=user.tenant_id,
        session_id=session.id,
        trace_id=trace_id,
        knowledge_base_ids=body.knowledge_base_ids or [],
        retrieved_context=[],  # TODO: Implement RAG retrieval
    )
    
    # Build message history
    messages: list[ChatMessage] = []
    
    if body.history:
        # Use provided history
        for msg in body.history:
            messages.append(ChatMessage(role=msg.role, content=msg.content))
    else:
        # Load history from database
        recent_messages = await message_repo.get_recent_messages(session.id, limit=20)
        for msg in recent_messages:
            messages.append(ChatMessage(role=msg.role.value, content=msg.content))
    
    # Add current user message
    messages.append(ChatMessage(role="user", content=body.message))
    
    # Store user message
    await message_repo.create(
        session_id=session.id,
        role=MessageRole.USER,
        content=body.message,
    )
    
    try:
        # Call the agent runtime
        response = await runtime.chat(
            messages=messages,
            context=context,
            model=body.model,
            temperature=body.temperature,
            max_tokens=body.max_tokens,
        )
        
        # Record token usage with rate limiter
        await rate_limiter.record_tokens(user.tenant_id, response.total_tokens)
        
        # Store assistant response
        assistant_message = await message_repo.create(
            session_id=session.id,
            role=MessageRole.ASSISTANT,
            content=response.content,
            model=response.model,
            prompt_tokens=response.prompt_tokens,
            completion_tokens=response.completion_tokens,
        )
        
        # Update session usage
        await session_repo.update_usage(
            session_id=session.id,
            tokens=response.total_tokens,
        )
        
        # Record usage for FinOps
        await usage_repo.record(
            user_id=user.sub,
            tenant_id=user.tenant_id,
            session_id=session.id,
            model=response.model,
            operation="chat",
            prompt_tokens=response.prompt_tokens,
            completion_tokens=response.completion_tokens,
            latency_ms=int(response.latency_ms),
            trace_id=trace_id,
        )
        
        # Commit all changes
        await db.commit()
        
        # Auto-generate title for new sessions
        if created and not session.title:
            # Use first ~50 chars of user message as title
            title = body.message[:50] + ("..." if len(body.message) > 50 else "")
            await session_repo.set_title(session.id, title)
            await db.commit()
        
        return ChatResponse(
            session_id=session.id,
            message_id=assistant_message.id,
            content=response.content,
            model=response.model,
            sources=None,  # TODO: Add sources from RAG
            usage={
                "prompt_tokens": response.prompt_tokens,
                "completion_tokens": response.completion_tokens,
                "total_tokens": response.total_tokens,
            },
            latency_ms=response.latency_ms,
            created_at=datetime.utcnow().isoformat() + "Z"
        )
        
    except RateLimitExceeded as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=str(e),
            headers={"Retry-After": str(e.retry_after)},
        )
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Chat completion failed: {str(e)}"
        )


@router.post("/chat/stream")
async def chat_stream(
    body: ChatRequest,
    user: CurrentUser,
    runtime: Runtime,
    db: DB,
    rate_limiter: RateLimiter,
    session_repo: SessionRepo,
    message_repo: MessageRepo,
):
    """Stream a chat response using Server-Sent Events (SSE).
    
    Returns a streaming response with chunks of the AI's response
    as they are generated.
    
    Event format:
    - data: {"content": "chunk"} - Content chunk
    - data: {"done": true, "usage": {...}} - Final event with usage stats
    - data: [DONE] - Stream complete
    """
    message_id = str(uuid4())
    trace_id = str(uuid4())
    
    # Check rate limits
    try:
        await rate_limiter.check_request_limit(user.tenant_id)
    except RateLimitExceeded as e:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=str(e),
            headers={"Retry-After": str(e.retry_after)},
        )
    
    # Get or create session
    session, created = await session_repo.get_or_create(
        session_id=body.session_id,
        user_id=user.sub,
        knowledge_base_ids=body.knowledge_base_ids,
    )
    
    # Build context
    context = ChatContext(
        user_id=user.sub,
        tenant_id=user.tenant_id,
        session_id=session.id,
        trace_id=trace_id,
        knowledge_base_ids=body.knowledge_base_ids or [],
        retrieved_context=[],
    )
    
    # Build message history
    messages: list[ChatMessage] = []
    
    if body.history:
        for msg in body.history:
            messages.append(ChatMessage(role=msg.role, content=msg.content))
    else:
        recent_messages = await message_repo.get_recent_messages(session.id, limit=20)
        for msg in recent_messages:
            messages.append(ChatMessage(role=msg.role.value, content=msg.content))
    
    messages.append(ChatMessage(role="user", content=body.message))
    
    # Store user message
    await message_repo.create(
        session_id=session.id,
        role=MessageRole.USER,
        content=body.message,
    )
    await db.commit()
    
    async def generate():
        """Generate SSE events from streaming response."""
        full_content = ""
        total_tokens = 0
        
        try:
            async for chunk in runtime.chat_stream(
                messages=messages,
                context=context,
                model=body.model,
                temperature=body.temperature,
                max_tokens=body.max_tokens,
            ):
                if chunk.content:
                    full_content += chunk.content
                    event_data = {"content": chunk.content}
                    yield f"data: {json.dumps(event_data)}\n\n"
                
                if chunk.finish_reason:
                    # Store assistant message
                    await message_repo.create(
                        session_id=session.id,
                        role=MessageRole.ASSISTANT,
                        content=full_content,
                    )
                    
                    # Update session
                    await session_repo.update_usage(session.id, tokens=len(full_content) // 4)
                    await db.commit()
                    
                    # Send final event
                    final_data = {
                        "done": True,
                        "session_id": session.id,
                        "message_id": message_id,
                        "finish_reason": chunk.finish_reason,
                    }
                    yield f"data: {json.dumps(final_data)}\n\n"
            
            yield "data: [DONE]\n\n"
            
        except Exception as e:
            error_data = {"error": str(e)}
            yield f"data: {json.dumps(error_data)}\n\n"
            yield "data: [DONE]\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        }
    )
