'use client';

import { useEffect, useRef } from 'react';
import { useChat } from '@/lib/hooks/useChat';
import { MessageBubble } from './MessageBubble';
import { MessageInput } from './MessageInput';
import { StreamingMessage } from './StreamingMessage';

interface ChatAreaProps {
  sessionId: string | null;
  onSessionCreated: (id: string, title?: string) => void;
}

export function ChatArea({ sessionId, onSessionCreated }: ChatAreaProps) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const { messages, isStreaming, isLoadingHistory, streamingContent, error, sendMessage } = useChat({
    sessionId,
    onSessionCreated,
  });

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, []);

  const handleSend = (content: string, knowledgeBaseIds?: string[]) => {
    if (content.trim() && !isStreaming && !isLoadingHistory) {
      sendMessage(content, knowledgeBaseIds);
    }
  };

  return (
    <div className="flex flex-1 flex-col min-h-0">
      {/* Messages Area */}
      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto px-4 py-6"
      >
        <div className="mx-auto max-w-3xl space-y-6">
          {isLoadingHistory ? (
            <div className="flex flex-col items-center justify-center py-16">
              <div className="size-8 animate-spin rounded-full border-2 border-neutral-600 border-t-neutral-300" />
              <p className="mt-4 text-sm text-neutral-500">Loading conversation...</p>
            </div>
          ) : messages.length === 0 && !isStreaming ? (
            <EmptyState />
          ) : (
            <>
              {messages.map((message) => (
                <MessageBubble
                  key={message.id}
                  message={message}
                  onFollowUpClick={(question) => handleSend(question)}
                />
              ))}

              {isStreaming && streamingContent && (
                <StreamingMessage content={streamingContent} />
              )}
            </>
          )}

          {error && (
            <div className="rounded-lg border border-red-900/50 bg-red-950/30 px-4 py-3 text-sm text-red-300">
              {error}
            </div>
          )}
        </div>
      </div>

      {/* Input Area */}
      <div className="flex-shrink-0 border-t border-neutral-800 bg-neutral-900/50 px-4 py-4">
        <div className="mx-auto max-w-3xl">
          <MessageInput
            onSend={handleSend}
            disabled={isStreaming || isLoadingHistory}
            placeholder="Send a message..."
          />
        </div>
      </div>
    </div>
  );
}

function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      <div className="mb-6 flex size-20 items-center justify-center rounded-2xl bg-gradient-to-br from-neutral-800 to-neutral-900 ring-1 ring-neutral-700/50">
        <svg
          className="size-10 text-neutral-400"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={1.25}
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M9.813 15.904 9 18.75l-.813-2.846a4.5 4.5 0 0 0-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 0 0 3.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 0 0 3.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 0 0-3.09 3.09ZM18.259 8.715 18 9.75l-.259-1.035a3.375 3.375 0 0 0-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 0 0 2.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 0 0 2.456 2.456L21.75 6l-1.035.259a3.375 3.375 0 0 0-2.456 2.456ZM16.894 20.567 16.5 21.75l-.394-1.183a2.25 2.25 0 0 0-1.423-1.423L13.5 18.75l1.183-.394a2.25 2.25 0 0 0 1.423-1.423l.394-1.183.394 1.183a2.25 2.25 0 0 0 1.423 1.423l1.183.394-1.183.394a2.25 2.25 0 0 0-1.423 1.423Z"
          />
        </svg>
      </div>
      <h2 className="mb-2 text-xl font-semibold text-neutral-100">
        How can I help you today?
      </h2>
      <p className="max-w-md text-sm text-neutral-500 text-pretty mb-6">
        Ask questions, analyze documents, or get help with tasks.
        Select a knowledge base below to search your documents.
      </p>

      {/* Quick Tips */}
      <div className="grid gap-2 text-left max-w-sm w-full">
        <div className="flex items-start gap-3 rounded-lg border border-neutral-800 bg-neutral-900/50 p-3">
          <div className="flex size-6 items-center justify-center rounded bg-blue-600/10 text-blue-400">
            <svg className="size-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 18v-5.25m0 0a6.01 6.01 0 0 0 1.5-.189m-1.5.189a6.01 6.01 0 0 1-1.5-.189m3.75 7.478a12.06 12.06 0 0 1-4.5 0m3.75 2.383a14.406 14.406 0 0 1-3 0M14.25 18v-.192c0-.983.658-1.823 1.508-2.316a7.5 7.5 0 1 0-7.517 0c.85.493 1.509 1.333 1.509 2.316V18" />
            </svg>
          </div>
          <div>
            <p className="text-xs font-medium text-neutral-300">Use Knowledge Bases</p>
            <p className="text-xs text-neutral-500">Click "Knowledge" to search your uploaded documents</p>
          </div>
        </div>
      </div>
    </div>
  );
}
