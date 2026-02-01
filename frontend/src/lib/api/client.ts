const API_BASE = process.env.NEXT_PUBLIC_API_URL || '';

export class APIError extends Error {
  constructor(
    public status: number,
    public data: unknown
  ) {
    super(`API Error: ${status}`);
    this.name = 'APIError';
  }
}

/**
 * Get authorization header for API requests
 * In production, this will be the session token from better-auth
 * In development, can use X-Dev-Bypass header
 */
function getAuthHeaders(): Record<string, string> {
  // In development, use bypass header
  if (process.env.NODE_ENV === 'development') {
    return { 'X-Dev-Bypass': 'true' };
  }
  
  // In production, session cookie is automatically included
  // The backend validates the session via the cookie
  return {};
}

export async function apiClient<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    credentials: 'include', // Include cookies for session auth
    headers: {
      'Content-Type': 'application/json',
      ...getAuthHeaders(),
      ...options.headers,
    },
  });

  if (!response.ok) {
    let data;
    try {
      data = await response.json();
    } catch {
      data = { detail: response.statusText };
    }
    throw new APIError(response.status, data);
  }

  return response.json();
}

interface StreamChunk {
  content?: string;
  done?: boolean;
  error?: string;
  session_id?: string;
}

export async function* streamChat(
  message: string,
  sessionId?: string
): AsyncGenerator<StreamChunk> {
  const response = await fetch(`${API_BASE}/api/v1/chat/stream`, {
    method: 'POST',
    credentials: 'include', // Include cookies for session auth
    headers: {
      'Content-Type': 'application/json',
      ...getAuthHeaders(),
    },
    body: JSON.stringify({
      message,
      session_id: sessionId,
      stream: true,
    }),
  });

  if (!response.ok) {
    const error = await response.json();
    yield { error: error.detail || 'Request failed' };
    return;
  }

  const reader = response.body?.getReader();
  if (!reader) {
    yield { error: 'No response body' };
    return;
  }

  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop() || '';

    for (const line of lines) {
      if (line.startsWith('data: ')) {
        const data = line.slice(6);
        if (data === '[DONE]') {
          yield { done: true };
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
