'use client';

import { useState } from 'react';
import { code } from '@streamdown/code';
import { Streamdown } from 'streamdown';
import { getInitials, useUser } from '@/lib/contexts/UserContext';
import type { Message, Source } from '@/lib/types';
import { cn } from '@/lib/utils/cn';

interface MessageBubbleProps {
  message: Message;
}

function SourceBadge({ source }: { source: Source }) {
  const [isHovered, setIsHovered] = useState(false);

  return (
    <span className="relative inline-block">
      <button
        type="button"
        onMouseEnter={() => setIsHovered(true)}
        onMouseLeave={() => setIsHovered(false)}
        onFocus={() => setIsHovered(true)}
        onBlur={() => setIsHovered(false)}
        className="inline-flex items-center gap-1.5 rounded-md bg-neutral-700/50 px-2 py-1 text-xs font-medium text-neutral-300 transition-colors hover:bg-neutral-600/50 hover:text-neutral-100"
      >
        <span className="flex size-4 items-center justify-center rounded bg-neutral-600 text-[10px] font-bold">
          {source.ref}
        </span>
        <span className="max-w-[150px] truncate">{source.filename}</span>
        {source.page && (
          <span className="text-neutral-400">{source.page}</span>
        )}
      </button>

      {/* Hover Popover */}
      {isHovered && (
        <div className="absolute bottom-full left-0 z-50 mb-2 w-80 max-w-[90vw] animate-in fade-in-0 zoom-in-95 duration-150">
          <div className="rounded-lg border border-neutral-700 bg-neutral-800 p-3 shadow-xl">
            {/* Header */}
            <div className="mb-2 flex items-start justify-between gap-2">
              <div className="flex items-center gap-2">
                <span className="flex size-5 items-center justify-center rounded bg-blue-600 text-xs font-bold text-white">
                  {source.ref}
                </span>
                <span className="text-sm font-medium text-neutral-100 truncate max-w-[200px]">
                  {source.filename}
                </span>
              </div>
              {source.page && (
                <span className="flex-shrink-0 rounded bg-neutral-700 px-1.5 py-0.5 text-xs text-neutral-300">
                  {source.page}
                </span>
              )}
            </div>

            {/* Excerpt */}
            <div className="text-xs text-neutral-400 leading-relaxed max-h-40 overflow-y-auto">
              {source.excerpt}
            </div>

            {/* Score indicator */}
            <div className="mt-2 flex items-center gap-2 text-[10px] text-neutral-500">
              <span>Relevance:</span>
              <div className="flex-1 h-1 bg-neutral-700 rounded-full overflow-hidden">
                <div
                  className="h-full bg-blue-500 rounded-full"
                  style={{ width: `${Math.min(source.score * 100, 100)}%` }}
                />
              </div>
              <span>{Math.round(source.score * 100)}%</span>
            </div>
          </div>
          {/* Arrow */}
          <div className="absolute left-4 top-full -mt-1 size-2 rotate-45 border-b border-r border-neutral-700 bg-neutral-800" />
        </div>
      )}
    </span>
  );
}

function SourcesList({ sources }: { sources: Source[] }) {
  if (!sources || sources.length === 0) return null;

  return (
    <div className="mt-3 border-t border-neutral-700/50 pt-3">
      <div className="mb-2 text-xs font-medium text-neutral-400">Sources</div>
      <div className="flex flex-wrap gap-2">
        {sources.map((source) => (
          <SourceBadge key={source.ref} source={source} />
        ))}
      </div>
    </div>
  );
}

export function MessageBubble({ message }: MessageBubbleProps) {
  const { user } = useUser();
  const isUser = message.role === 'user';

  // Get user initials or fallback to 'U'
  const userInitials = user ? getInitials(user.name) : 'U';

  return (
    <div
      className={cn(
        'flex gap-3',
        isUser && 'flex-row-reverse'
      )}
    >
      {/* Avatar */}
      <div
        className={cn(
          'flex size-8 flex-shrink-0 items-center justify-center rounded-full text-xs font-medium',
          isUser
            ? 'bg-blue-600 text-white'
            : 'bg-neutral-700 text-neutral-300'
        )}
      >
        {isUser ? userInitials : 'AI'}
      </div>

      {/* Message Content */}
      <div
        className={cn(
          'max-w-[75%] rounded-2xl px-4 py-2.5',
          isUser
            ? 'bg-blue-600 text-white'
            : 'bg-neutral-800 text-neutral-100'
        )}
      >
        {isUser ? (
          // User messages: plain text, no markdown
          <div className="whitespace-pre-wrap text-sm leading-relaxed text-pretty">
            {message.content}
          </div>
        ) : (
          // AI messages: render markdown with streamdown
          <div className="prose prose-invert prose-sm max-w-none">
            <Streamdown plugins={{ code }}>
              {message.content}
            </Streamdown>
          </div>
        )}

        {/* Sources with hover popovers */}
        {!isUser && message.sources && message.sources.length > 0 && (
          <SourcesList sources={message.sources} />
        )}

        {message.timestamp && formatTime(message.timestamp) && (
          <div
            className={cn(
              'mt-1.5 text-[10px]',
              isUser ? 'text-blue-200' : 'text-neutral-500'
            )}
          >
            {formatTime(message.timestamp)}
          </div>
        )}
      </div>
    </div>
  );
}

function formatTime(timestamp: string): string {
  if (!timestamp) return '';

  const date = new Date(timestamp);

  // Check for invalid date
  if (Number.isNaN(date.getTime())) {
    return '';
  }

  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}
