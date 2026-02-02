const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

export class APIError extends Error {
  constructor(
    public status: number,
    public data: unknown,
  ) {
    super(`API Error: ${status}`);
    this.name = "APIError";
  }
}

/**
 * Get authorization header for API requests
 *
 * Authentication is handled via:
 * 1. better-auth session cookies (SSO) - automatically included via credentials: 'include'
 * 2. Backend falls back to dev user in development mode if no valid session
 *
 * Note: We don't send X-Dev-Bypass automatically because it would override valid SSO sessions.
 * The backend handles the fallback logic.
 */
function getAuthHeaders(): Record<string, string> {
  // Let cookies handle auth - backend will use session cookie or fall back to dev user
  return {};
}

export async function apiClient<T>(
  endpoint: string,
  options: RequestInit = {},
): Promise<T> {
  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    credentials: "include", // Include cookies for session auth
    headers: {
      "Content-Type": "application/json",
      ...getAuthHeaders(),
      ...options.headers,
    },
  });

  if (!response.ok) {
    let data: unknown;
    try {
      data = await response.json();
    } catch {
      data = { detail: response.statusText };
    }
    throw new APIError(response.status, data);
  }

  // Handle 204 No Content (e.g., DELETE responses)
  if (response.status === 204) {
    return undefined as T;
  }

  return response.json();
}

interface StreamChunk {
  content?: string;
  done?: boolean;
  error?: string;
  session_id?: string;
  title?: string; // Auto-generated title for new sessions
}

export async function* streamChat(
  message: string,
  sessionId?: string,
  knowledgeBaseIds?: string[],
): AsyncGenerator<StreamChunk> {
  const response = await fetch(`${API_BASE}/api/v1/chat/stream`, {
    method: "POST",
    credentials: "include", // Include cookies for session auth
    headers: {
      "Content-Type": "application/json",
      ...getAuthHeaders(),
    },
    body: JSON.stringify({
      message,
      session_id: sessionId,
      stream: true,
      ...(knowledgeBaseIds?.length && { knowledge_base_ids: knowledgeBaseIds }),
    }),
  });

  if (!response.ok) {
    const error = await response.json();
    yield { error: error.detail || "Request failed" };
    return;
  }

  const reader = response.body?.getReader();
  if (!reader) {
    yield { error: "No response body" };
    return;
  }

  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() || "";

    for (const line of lines) {
      if (line.startsWith("data: ")) {
        const data = line.slice(6);
        if (data === "[DONE]") {
          // Just return - the done signal was already sent in the JSON event
          return;
        }
        try {
          const parsed = JSON.parse(data);
          yield parsed;
        } catch {
          // Skip invalid JSON
        }
      }
    }
  }
}
