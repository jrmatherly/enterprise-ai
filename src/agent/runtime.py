"""Agent runtime for LLM interactions.

Handles chat completions with Azure AI Foundry, including:
- Multi-region routing
- Langfuse observability
- Conversation history management
- RAG context injection
"""

import time
from collections.abc import AsyncGenerator
from dataclasses import dataclass, field

from langfuse import Langfuse
from openai import AsyncAzureOpenAI

from src.core.config import get_settings


@dataclass
class ChatMessage:
    """A message in a conversation."""

    role: str  # system, user, assistant, tool
    content: str
    name: str | None = None
    tool_calls: list | None = None
    tool_call_id: str | None = None


@dataclass
class ChatContext:
    """Context for a chat request."""

    user_id: str
    tenant_id: str
    session_id: str
    trace_id: str
    knowledge_base_ids: list[str] = field(default_factory=list)
    retrieved_context: list[dict] = field(default_factory=list)
    kb_instructions: str = ""
    grounded_only: bool = False


@dataclass
class ChatResponse:
    """Response from a chat completion."""

    content: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    latency_ms: float
    finish_reason: str
    tool_calls: list | None = None


@dataclass
class StreamChunk:
    """A chunk of a streaming response."""

    content: str
    finish_reason: str | None = None
    tool_calls: list | None = None


class AgentRuntime:
    """Runtime for AI agent interactions.

    Provides a high-level interface for:
    - Chat completions with Azure AI Foundry
    - Streaming responses
    - Langfuse tracing
    - Multi-region routing
    """

    def __init__(self):
        self.settings = get_settings()
        self._clients: dict[str, AsyncAzureOpenAI] = {}
        self._langfuse: Langfuse | None = None

        # Initialize clients
        self._init_clients()
        self._init_langfuse()

    def _init_clients(self) -> None:
        """Initialize Azure OpenAI clients for each region."""
        # East US
        if self.settings.azure_ai_eastus_endpoint:
            self._clients["eastus"] = AsyncAzureOpenAI(
                azure_endpoint=self.settings.azure_ai_eastus_endpoint,
                api_key=self.settings.azure_ai_eastus_api_key,
                api_version=self.settings.azure_openai_api_version,
            )

        # East US 2
        if self.settings.azure_ai_eastus2_endpoint:
            self._clients["eastus2"] = AsyncAzureOpenAI(
                azure_endpoint=self.settings.azure_ai_eastus2_endpoint,
                api_key=self.settings.azure_ai_eastus2_api_key,
                api_version=self.settings.azure_openai_api_version,
            )

    def _init_langfuse(self) -> None:
        """Initialize Langfuse for observability."""
        if self.settings.langfuse_public_key and self.settings.langfuse_secret_key:
            self._langfuse = Langfuse(
                public_key=self.settings.langfuse_public_key,
                secret_key=self.settings.langfuse_secret_key,
                host=self.settings.langfuse_host,
            )

    def _get_client(self, model: str) -> tuple[AsyncAzureOpenAI, str]:
        """Get the appropriate client for a model.

        Uses model routing configuration to pick the right region.

        Returns:
            Tuple of (client, region)
        """
        routing = self.settings.get_model_routing()
        region = routing.get(model, self.settings.azure_ai_default_region)

        client = self._clients.get(region)
        if not client:
            # Fallback to any available client
            if self._clients:
                region = next(iter(self._clients.keys()))
                client = self._clients[region]
            else:
                raise RuntimeError("No Azure AI clients configured")

        return client, region

    def _build_system_prompt(self, context: ChatContext) -> str:
        """Build the system prompt with RAG context and KB instructions."""
        # Use minimal base when KB provides custom instructions (allows persona override)
        if context.kb_instructions:
            base_prompt = "Follow the instructions below for this conversation."
        else:
            base_prompt = """You are an intelligent AI assistant for an enterprise organization.
You help users with their questions by providing accurate, helpful, and professional responses.

Key behaviors:
- Be concise but thorough
- Cite sources when using retrieved context
- If you don't know something, say so
- Follow organizational policies and guidelines
- Protect sensitive information"""

        # Add grounding constraints if enabled (must come before KB instructions)
        if context.grounded_only:
            base_prompt += """

CRITICAL CONSTRAINT - GROUNDED RESPONSES ONLY:
You must ONLY respond using information from the <retrieved_context> section below.
- If the answer is not found in <retrieved_context>, clearly state: "I don't have information about that in my knowledge base."
- Do NOT use external knowledge, general information, or make assumptions beyond what is explicitly stated in <retrieved_context>.
- Do NOT offer to help with topics outside the <retrieved_context>.
- Every claim must be traceable to a specific source in <retrieved_context>."""

        # Add knowledge base custom instructions if provided
        if context.kb_instructions:
            base_prompt += f"""

## Knowledge Base Instructions
{context.kb_instructions}"""

        # Add retrieved context if available (wrapped in tags for clear reference)
        if context.retrieved_context:
            context_text = "\n\n".join(
                [
                    f"[Source: {doc.get('filename', 'Unknown')}]\n{doc.get('content', '')}"
                    for doc in context.retrieved_context
                ]
            )
            base_prompt += f"""

<retrieved_context>
{context_text}
</retrieved_context>

When responding, cite sources from <retrieved_context> using the format: [Source: filename]."""

        return base_prompt

    async def chat(
        self,
        messages: list[ChatMessage],
        context: ChatContext,
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> ChatResponse:
        """Send a chat completion request.

        Args:
            messages: Conversation history
            context: Request context (user, tenant, session info)
            model: Model to use (defaults to configured default)
            temperature: Sampling temperature
            max_tokens: Maximum tokens in response

        Returns:
            ChatResponse with content and usage info
        """
        model = model or self.settings.azure_ai_default_model
        client, region = self._get_client(model)

        # Build messages with system prompt
        system_prompt = self._build_system_prompt(context)
        api_messages = [{"role": "system", "content": system_prompt}]

        for msg in messages:
            api_msg = {"role": msg.role, "content": msg.content}
            if msg.name:
                api_msg["name"] = msg.name
            if msg.tool_calls:
                api_msg["tool_calls"] = msg.tool_calls
            if msg.tool_call_id:
                api_msg["tool_call_id"] = msg.tool_call_id
            api_messages.append(api_msg)

        # Create Langfuse generation if available
        generation = None
        if self._langfuse:
            try:
                generation = self._langfuse.start_generation(
                    name="llm-call",
                    model=model,
                    input=api_messages,
                    metadata={
                        "trace_id": context.trace_id,
                        "user_id": context.user_id,
                        "tenant_id": context.tenant_id,
                        "session_id": context.session_id,
                        "region": region,
                    },
                )
            except Exception as e:
                # Langfuse errors shouldn't break the chat flow
                print(f"Langfuse generation start failed: {e}")

        # Make the API call
        start_time = time.perf_counter()

        try:
            # Build request params - some models don't support all params
            create_params = {
                "model": model,
                "messages": api_messages,
            }
            # Only add optional params if they might be supported
            # Newer models (gpt-5, o-series) have limited param support
            if not any(x in model.lower() for x in ["gpt-5", "o1", "o3"]):
                create_params["temperature"] = temperature
                create_params["max_tokens"] = max_tokens
            else:
                # For newer models, use max_completion_tokens
                create_params["max_completion_tokens"] = max_tokens

            response = await client.chat.completions.create(**create_params)

            latency_ms = (time.perf_counter() - start_time) * 1000

            # Extract response
            choice = response.choices[0]
            usage = response.usage

            result = ChatResponse(
                content=choice.message.content or "",
                model=response.model,
                prompt_tokens=usage.prompt_tokens,
                completion_tokens=usage.completion_tokens,
                total_tokens=usage.total_tokens,
                latency_ms=latency_ms,
                finish_reason=choice.finish_reason,
                tool_calls=choice.message.tool_calls
                if hasattr(choice.message, "tool_calls")
                else None,
            )

            # Update Langfuse generation
            if generation:
                generation.update(
                    output=result.content,
                    usage={
                        "input": usage.prompt_tokens,
                        "output": usage.completion_tokens,
                        "total": usage.total_tokens,
                    },
                    metadata={
                        "finish_reason": choice.finish_reason,
                        "latency_ms": latency_ms,
                    },
                )
                generation.end()

            return result

        except Exception as e:
            if generation:
                generation.update(
                    level="ERROR",
                    status_message=str(e),
                )
                generation.end()
            raise

    async def chat_stream(
        self,
        messages: list[ChatMessage],
        context: ChatContext,
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> AsyncGenerator[StreamChunk, None]:
        """Stream a chat completion response.

        Args:
            messages: Conversation history
            context: Request context
            model: Model to use
            temperature: Sampling temperature
            max_tokens: Maximum tokens in response

        Yields:
            StreamChunk objects with content fragments
        """
        model = model or self.settings.azure_ai_default_model
        client, region = self._get_client(model)

        # Build messages with system prompt
        system_prompt = self._build_system_prompt(context)
        api_messages = [{"role": "system", "content": system_prompt}]

        for msg in messages:
            api_msg = {"role": msg.role, "content": msg.content}
            api_messages.append(api_msg)

        # Create Langfuse generation if available
        generation = None
        if self._langfuse:
            try:
                generation = self._langfuse.start_generation(
                    name="llm-call-stream",
                    model=model,
                    input=api_messages,
                    metadata={
                        "trace_id": context.trace_id,
                        "user_id": context.user_id,
                        "tenant_id": context.tenant_id,
                        "session_id": context.session_id,
                        "region": region,
                        "streaming": True,
                    },
                )
            except Exception as e:
                print(f"Langfuse generation start failed: {e}")

        # Stream the response
        full_content = ""
        start_time = time.perf_counter()

        try:
            # Build request params - some models don't support all params
            create_params = {
                "model": model,
                "messages": api_messages,
                "stream": True,
            }
            if not any(x in model.lower() for x in ["gpt-5", "o1", "o3"]):
                create_params["temperature"] = temperature
                create_params["max_tokens"] = max_tokens
            else:
                create_params["max_completion_tokens"] = max_tokens

            stream = await client.chat.completions.create(**create_params)

            async for chunk in stream:
                if chunk.choices:
                    delta = chunk.choices[0].delta
                    finish_reason = chunk.choices[0].finish_reason

                    content = delta.content or ""
                    full_content += content

                    yield StreamChunk(
                        content=content,
                        finish_reason=finish_reason,
                        tool_calls=delta.tool_calls if hasattr(delta, "tool_calls") else None,
                    )

            latency_ms = (time.perf_counter() - start_time) * 1000

            # Update Langfuse generation
            if generation:
                generation.update(
                    output=full_content,
                    metadata={
                        "latency_ms": latency_ms,
                        "streaming": True,
                    },
                )
                generation.end()

        except Exception as e:
            if generation:
                generation.update(
                    level="ERROR",
                    status_message=str(e),
                )
                generation.end()
            raise

    async def shutdown(self) -> None:
        """Cleanup resources."""
        if self._langfuse:
            self._langfuse.flush()

        for client in self._clients.values():
            await client.close()


# Global runtime instance
_runtime: AgentRuntime | None = None


def get_runtime() -> AgentRuntime:
    """Get or create the global agent runtime."""
    global _runtime
    if _runtime is None:
        _runtime = AgentRuntime()
    return _runtime


async def shutdown_runtime() -> None:
    """Shutdown the global runtime."""
    global _runtime
    if _runtime:
        await _runtime.shutdown()
        _runtime = None
