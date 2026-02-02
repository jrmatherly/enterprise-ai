"use client";

import { useQueryClient } from "@tanstack/react-query";
import { useCallback, useEffect, useState } from "react";
import { apiClient, streamChat } from "@/lib/api/client";
import type { Message, Source } from "@/lib/types";

interface UseChatOptions {
  sessionId: string | null;
  onSessionCreated: (id: string, title?: string) => void;
}

interface SessionDetail {
  id: string;
  title: string | null;
  messages: Array<{
    id: string;
    role: string;
    content: string;
    created_at: string;
  }>;
}

export function useChat({ sessionId, onSessionCreated }: UseChatOptions) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamingContent, setStreamingContent] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);
  const queryClient = useQueryClient();

  // Track if we just created a new session (to avoid reloading and losing sources)
  const [justCreatedSession, setJustCreatedSession] = useState(false);

  // Load session history when sessionId changes
  useEffect(() => {
    if (!sessionId) {
      setMessages([]);
      setJustCreatedSession(false);
      return;
    }

    // Skip loading history if we just created this session
    // (we already have the messages with sources from streaming)
    if (justCreatedSession) {
      setJustCreatedSession(false);
      return;
    }

    const loadHistory = async () => {
      setIsLoadingHistory(true);
      setError(null);

      try {
        const session = await apiClient<SessionDetail>(
          `/api/v1/sessions/${sessionId}?include_messages=true`,
        );

        const loadedMessages: Message[] = session.messages.map((msg) => ({
          id: msg.id,
          role: msg.role as "user" | "assistant" | "system",
          content: msg.content,
          timestamp: msg.created_at,
        }));

        setMessages(loadedMessages);
      } catch (err) {
        console.error("Failed to load session history:", err);
        setError("Failed to load conversation history");
      } finally {
        setIsLoadingHistory(false);
      }
    };

    loadHistory();
  }, [sessionId, justCreatedSession]);

  const sendMessage = useCallback(
    async (content: string, knowledgeBaseIds?: string[]) => {
      if (!content.trim() || isStreaming) return;

      setError(null);

      // Add user message optimistically
      const userMessage: Message = {
        id: `user-${Date.now()}`,
        role: "user",
        content: content.trim(),
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, userMessage]);
      setIsStreaming(true);
      setStreamingContent("");

      try {
        let fullContent = "";
        let newSessionId: string | null = null;
        let messageSources: Source[] | undefined;

        for await (const chunk of streamChat(
          content,
          sessionId ?? undefined,
          knowledgeBaseIds,
        )) {
          if (chunk.error) {
            setError(chunk.error);
            setStreamingContent(null);
            break;
          }

          if (chunk.content) {
            fullContent += chunk.content;
            setStreamingContent(fullContent);
          }

          if (chunk.session_id) {
            newSessionId = chunk.session_id;
          }

          // Capture sources from the final chunk
          if (chunk.sources) {
            messageSources = chunk.sources;
          }

          if (chunk.done) {
            // Add completed assistant message with sources
            const assistantMessage: Message = {
              id: `assistant-${Date.now()}`,
              role: "assistant",
              content: fullContent,
              timestamp: new Date().toISOString(),
              sources: messageSources,
            };
            setMessages((prev) => [...prev, assistantMessage]);
            setStreamingContent(null);

            // Notify parent of new session (with title if generated)
            if (newSessionId && !sessionId) {
              // Mark that we just created this session so we don't reload
              // and lose the sources from the streaming response
              setJustCreatedSession(true);
              onSessionCreated(newSessionId, chunk.title);
            }

            // Refresh sessions list to show updated title
            queryClient.invalidateQueries({ queryKey: ["sessions"] });
          }
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to send message");
        setStreamingContent(null);
      } finally {
        setIsStreaming(false);
      }
    },
    [sessionId, isStreaming, onSessionCreated, queryClient],
  );

  const clearMessages = useCallback(() => {
    setMessages([]);
    setStreamingContent(null);
    setError(null);
  }, []);

  return {
    messages,
    isStreaming,
    isLoadingHistory,
    streamingContent,
    error,
    sendMessage,
    clearMessages,
  };
}
