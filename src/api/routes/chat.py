"""Chat/agent interaction endpoints."""

import json
from datetime import UTC, datetime
from uuid import uuid4

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from src.agent.runtime import AgentRuntime, ChatContext, ChatMessage
from src.api.deps import (
    DB,
    CurrentUser,
    MessageRepo,
    RateLimiter,
    RequireUseAgent,
    Runtime,
    SessionRepo,
    UsageRepo,
)
from src.core.rate_limiting import RateLimitExceeded
from src.db.models import MessageRole
from src.rag import get_retriever

router = APIRouter()


async def generate_session_title(
    runtime: AgentRuntime,
    user_message: str,
    assistant_response: str,
) -> str:
    """Generate a short, descriptive title for a chat session.

    Makes a direct LLM call (bypassing runtime's system prompt) to create
    a concise title (5-8 words) based on the first exchange.
    """
    from openai import AsyncAzureOpenAI

    from src.core.config import get_settings

    settings = get_settings()

    prompt = f"""Generate a very short title (5-8 words max) for this conversation.
Just output the title, nothing else. No quotes, no prefix.

User: {user_message[:300]}
Assistant: {assistant_response[:300]}

Title:"""

    try:
        # Create a direct client for this simple call
        client = AsyncAzureOpenAI(
            azure_endpoint=settings.azure_ai_eastus_endpoint or settings.azure_ai_eastus2_endpoint,
            api_key=settings.azure_ai_eastus_api_key or settings.azure_ai_eastus2_api_key,
            api_version=settings.azure_openai_api_version,
        )

        model = settings.azure_ai_default_model

        # Build request - handle different model types
        create_params = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
        }
        if not any(x in model.lower() for x in ["gpt-5", "o1", "o3"]):
            create_params["temperature"] = 0.3
            create_params["max_tokens"] = 30
        else:
            create_params["max_completion_tokens"] = 30

        response = await client.chat.completions.create(**create_params)
        await client.close()

        content = response.choices[0].message.content or ""

        # Clean up the title
        title = content.strip()
        title = title.strip("\"'")
        if len(title) > 100:
            title = title[:97] + "..."

        return title if title else user_message[:50]

    except Exception:
        # Fallback to first part of user message
        return user_message[:50] + ("..." if len(user_message) > 50 else "")


class ChatMessageInput(BaseModel):
    """A single chat message for input."""

    role: str = Field(..., description="Message role: user, assistant, or system")
    content: str = Field(..., description="Message content")


class ChatRequest(BaseModel):
    """Chat completion request."""

    message: str = Field(..., description="User message", max_length=32000)
    session_id: str | None = Field(None, description="Session ID for conversation continuity")
    stream: bool = Field(False, description="Whether to stream the response")
    knowledge_base_ids: list[str] | None = Field(
        None, description="Knowledge base IDs to search for context"
    )
    model: str | None = Field(None, description="Model to use (uses default if not specified)")
    temperature: float = Field(0.7, ge=0.0, le=2.0, description="Sampling temperature")
    max_tokens: int = Field(4096, ge=1, le=128000, description="Maximum tokens in response")
    history: list[ChatMessageInput] | None = Field(
        None, description="Previous conversation messages (overrides stored history)"
    )


class ChatResponse(BaseModel):
    """Chat completion response."""

    session_id: str
    message_id: str
    content: str
    model: str
    sources: list[dict] | None = None
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
    return await rate_limiter.get_usage(user.tenant_id)


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
    _: bool = RequireUseAgent,
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
    str(uuid4())
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
        ) from None

    # Get or create session
    session, created = await session_repo.get_or_create(
        session_id=body.session_id,
        user_id=user.sub,
        knowledge_base_ids=body.knowledge_base_ids,
    )

    # Perform RAG retrieval if knowledge bases specified
    retrieved_context = []
    rag_context_text = ""
    if body.knowledge_base_ids:
        try:
            retriever = await get_retriever()
            chunks = await retriever.retrieve(
                query=body.message,
                knowledge_base_ids=body.knowledge_base_ids,
                user_id=user.sub,
                tenant_id=user.tenant_id,
                group_ids=user.groups,
                limit=5,
                score_threshold=0.5,
            )
            retrieved_context = [
                {"text": c.text, "score": c.score, "document_id": c.document_id} for c in chunks
            ]
            rag_context_text = retriever.format_context(chunks)
        except Exception as e:
            # Log but continue without RAG
            print(f"RAG retrieval failed: {e}")

    # Build context
    context = ChatContext(
        user_id=user.sub,
        tenant_id=user.tenant_id,
        session_id=session.id,
        trace_id=trace_id,
        knowledge_base_ids=body.knowledge_base_ids or [],
        retrieved_context=retrieved_context,
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

    # Add RAG context as system message if available
    if rag_context_text:
        rag_system_msg = (
            "Use the following retrieved context to help answer the user's question. "
            "If the context doesn't contain relevant information, say so and answer "
            "based on your general knowledge.\n\n"
            f"Retrieved Context:\n{rag_context_text}"
        )
        messages.append(ChatMessage(role="system", content=rag_system_msg))

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
            title = await generate_session_title(runtime, body.message, response.content)
            await session_repo.set_title(session.id, title)
            await db.commit()

        # Build sources from retrieved context
        sources = None
        if retrieved_context:
            # Get document info for sources
            from sqlalchemy import select

            from src.db.models import Document

            doc_ids = list({r["document_id"] for r in retrieved_context})
            doc_query = select(Document).where(Document.id.in_(doc_ids))
            doc_result = await db.execute(doc_query)
            docs = {d.id: d for d in doc_result.scalars().all()}

            sources = [
                {
                    "document_id": r["document_id"],
                    "filename": docs.get(
                        r["document_id"], type("", (), {"filename": "unknown"})
                    ).filename,
                    "score": round(r["score"], 3),
                    "excerpt": r["text"][:200] + "..." if len(r["text"]) > 200 else r["text"],
                }
                for r in retrieved_context[:5]  # Top 5 sources
            ]

        return ChatResponse(
            session_id=session.id,
            message_id=assistant_message.id,
            content=response.content,
            model=response.model,
            sources=sources,
            usage={
                "prompt_tokens": response.prompt_tokens,
                "completion_tokens": response.completion_tokens,
                "total_tokens": response.total_tokens,
            },
            latency_ms=response.latency_ms,
            created_at=datetime.now(UTC).isoformat() + "Z",
        )

    except RateLimitExceeded as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=str(e),
            headers={"Retry-After": str(e.retry_after)},
        ) from None
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Chat completion failed: {e!s}",
        ) from None


@router.post("/chat/stream")
async def chat_stream(
    body: ChatRequest,
    user: CurrentUser,
    runtime: Runtime,
    db: DB,
    rate_limiter: RateLimiter,
    session_repo: SessionRepo,
    message_repo: MessageRepo,
    _: bool = RequireUseAgent,
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
        ) from None

    # Get or create session
    session, created = await session_repo.get_or_create(
        session_id=body.session_id,
        user_id=user.sub,
        knowledge_base_ids=body.knowledge_base_ids,
    )

    # Perform RAG retrieval if knowledge bases specified
    retrieved_context = []
    rag_context_text = ""
    if body.knowledge_base_ids:
        try:
            retriever = await get_retriever()
            chunks = await retriever.retrieve(
                query=body.message,
                knowledge_base_ids=body.knowledge_base_ids,
                user_id=user.sub,
                tenant_id=user.tenant_id,
                group_ids=user.groups,
                limit=5,
                score_threshold=0.5,
            )
            retrieved_context = [
                {"text": c.text, "score": c.score, "document_id": c.document_id} for c in chunks
            ]
            rag_context_text = retriever.format_context(chunks)
        except Exception as e:
            print(f"RAG retrieval failed: {e}")

    # Build context
    context = ChatContext(
        user_id=user.sub,
        tenant_id=user.tenant_id,
        session_id=session.id,
        trace_id=trace_id,
        knowledge_base_ids=body.knowledge_base_ids or [],
        retrieved_context=retrieved_context,
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

    # Add RAG context as system message if available
    if rag_context_text:
        rag_system_msg = (
            "Use the following retrieved context to help answer the user's question. "
            "If the context doesn't contain relevant information, say so and answer "
            "based on your general knowledge.\n\n"
            f"Retrieved Context:\n{rag_context_text}"
        )
        messages.append(ChatMessage(role="system", content=rag_system_msg))

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

                    # Auto-generate title for new sessions
                    generated_title = None
                    if created and not session.title:
                        generated_title = await generate_session_title(
                            runtime, body.message, full_content
                        )
                        await session_repo.set_title(session.id, generated_title)

                    await db.commit()

                    # Send final event (include title if generated)
                    final_data = {
                        "done": True,
                        "session_id": session.id,
                        "message_id": message_id,
                        "finish_reason": chunk.finish_reason,
                    }
                    if generated_title:
                        final_data["title"] = generated_title
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
        },
    )
