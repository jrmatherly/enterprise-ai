"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/lib/api/client";

export interface Session {
  id: string;
  title: string | null;
  message_count: number;
  total_tokens: number;
  created_at: string;
  updated_at: string;
  last_message_at: string | null;
}

export interface SessionDetail extends Session {
  messages: Array<{
    id: string;
    role: string;
    content: string;
    created_at: string;
  }>;
}

/**
 * Fetch user's chat sessions
 */
export function useSessions(limit: number = 50) {
  return useQuery({
    queryKey: ["sessions", limit],
    queryFn: async () => {
      return apiClient<Session[]>(`/api/v1/sessions?limit=${limit}`);
    },
    staleTime: 30 * 1000, // Consider fresh for 30 seconds
    refetchOnWindowFocus: true,
  });
}

/**
 * Fetch a single session with messages
 */
export function useSession(sessionId: string | null) {
  return useQuery({
    queryKey: ["session", sessionId],
    queryFn: async () => {
      if (!sessionId) return null;
      return apiClient<SessionDetail>(
        `/api/v1/sessions/${sessionId}?include_messages=true`,
      );
    },
    enabled: !!sessionId,
    staleTime: 10 * 1000,
  });
}

/**
 * Create a new session
 */
export function useCreateSession() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: {
      title?: string;
      knowledge_base_ids?: string[];
    }) => {
      return apiClient<Session>("/api/v1/sessions", {
        method: "POST",
        body: JSON.stringify(data),
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["sessions"] });
    },
  });
}

/**
 * Update a session
 */
export function useUpdateSession() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      sessionId,
      title,
    }: {
      sessionId: string;
      title: string;
    }) => {
      return apiClient<Session>(`/api/v1/sessions/${sessionId}`, {
        method: "PATCH",
        body: JSON.stringify({ title }),
      });
    },
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ["sessions"] });
      queryClient.invalidateQueries({
        queryKey: ["session", variables.sessionId],
      });
    },
  });
}

/**
 * Delete a session
 */
export function useDeleteSession() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (sessionId: string) => {
      return apiClient<void>(`/api/v1/sessions/${sessionId}`, {
        method: "DELETE",
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["sessions"] });
    },
  });
}
