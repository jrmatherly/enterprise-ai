'use client';

import { useRef, useEffect } from 'react';
import { useChat } from '@/lib/hooks/useChat';
import { MessageBubble } from './MessageBubble';
import { MessageInput } from './MessageInput';
import { StreamingMessage } from './StreamingMessage';

interface ChatAreaProps {
  sessionId: string | null;
  onSessionCreated: (id: string) => void;
}

export function ChatArea({ sessionId, onSessionCreated }: ChatAreaProps) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const { messages, isStreaming, streamingContent, error, sendMessage } = useChat({
    sessionId,
    onSessionCreated,
  });

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, streamingContent]);

  const handleSend = (content: string) => {
    if (content.trim() && !isStreaming) {
      sendMessage(content);
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
          {messages.length === 0 && !isStreaming && (
            <EmptyState />
          )}
          
          {messages.map((message) => (
            <MessageBubble key={message.id} message={message} />
          ))}
          
          {isStreaming && streamingContent && (
            <StreamingMessage content={streamingContent} />
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
            disabled={isStreaming}
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
      <div className="mb-4 flex size-16 items-center justify-center rounded-xl bg-neutral-800">
        <svg
          className="size-8 text-neutral-500"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={1.5}
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M8.625 12a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm0 0H8.25m4.125 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm0 0H12m4.125 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm0 0h-.375M21 12c0 4.556-4.03 8.25-9 8.25a9.764 9.764 0 0 1-2.555-.337A5.972 5.972 0 0 1 5.41 20.97a5.969 5.969 0 0 1-.474-.065 4.48 4.48 0 0 0 .978-2.025c.09-.457-.133-.901-.467-1.226C3.93 16.178 3 14.189 3 12c0-4.556 4.03-8.25 9-8.25s9 3.694 9 8.25Z"
          />
        </svg>
      </div>
      <h2 className="mb-2 text-lg font-medium text-neutral-200">
        Start a conversation
      </h2>
      <p className="max-w-sm text-sm text-neutral-500 text-pretty">
        Ask questions, get help with tasks, or explore your knowledge bases.
      </p>
    </div>
  );
}
