export interface Message {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  timestamp?: string;
  sources?: Source[];
}

export interface Source {
  ref: number;
  document_id: string;
  filename: string;
  page: string | null;
  score: number;
  excerpt: string;
}

export interface Session {
  id: string;
  title: string | null;
  createdAt: string;
  updatedAt: string;
  totalTokens: number;
  messageCount?: number;
}

export interface ChatResponse {
  session_id: string;
  message_id: string;
  content: string;
  model: string;
  sources: Source[] | null;
  usage: {
    prompt_tokens: number;
    completion_tokens: number;
    total_tokens: number;
  };
  latency_ms: number;
  created_at: string;
}

export interface UsageInfo {
  tokens: {
    used: number;
    limit: number;
    remaining: number;
  };
  requests: {
    used: number;
    limit: number;
    remaining: number;
  };
}
