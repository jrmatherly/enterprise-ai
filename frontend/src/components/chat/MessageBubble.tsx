'use client';

import { useState } from 'react';
import { code } from '@streamdown/code';
import { Streamdown } from 'streamdown';
import { getInitials, useUser } from '@/lib/contexts/UserContext';
import type { Message, Source } from '@/lib/types';
import { cn } from '@/lib/utils/cn';

interface MessageBubbleProps {
  message: Message;
  onFollowUpClick?: (question: string) => void;
}

/**
 * Parse follow-up questions from message content.
 * Looks for <<<FOLLOWUP>>>...<<<END_FOLLOWUP>>> markers.
 */
function parseFollowUpQuestions(content: string): { cleanContent: string; questions: string[] } {
  const followUpRegex = /<<<FOLLOWUP>>>([\s\S]*?)<<<END_FOLLOWUP>>>/;
  const match = content.match(followUpRegex);

  if (!match) {
    return { cleanContent: content, questions: [] };
  }

  const cleanContent = content.replace(followUpRegex, '').trim();
  const questionsBlock = match[1].trim();
  const questions = questionsBlock
    .split('\n')
    .map(q => q.trim())
    .filter(q => q.length > 0 && !q.startsWith('-')); // Filter empty lines and bullet markers

  // Also handle bullet-style questions
  const bulletQuestions = questionsBlock
    .split('\n')
    .map(q => q.replace(/^[-•*]\s*/, '').trim())
    .filter(q => q.length > 0);

  return {
    cleanContent,
    questions: questions.length > 0 ? questions : bulletQuestions
  };
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

function FollowUpQuestions({
  questions,
  onQuestionClick
}: {
  questions: string[];
  onQuestionClick?: (question: string) => void;
}) {
  if (!questions || questions.length === 0) return null;

  return (
    <div className="mt-3 border-t border-neutral-700/50 pt-3">
      <div className="mb-2 text-xs font-medium text-neutral-400">Follow-up questions</div>
      <div className="flex flex-col gap-1.5">
        {questions.map((question, index) => (
          <button
            key={`followup-${index}`}
            type="button"
            onClick={() => onQuestionClick?.(question)}
            className="text-left text-sm text-blue-400 hover:text-blue-300 transition-colors py-1 px-2 -mx-2 rounded hover:bg-neutral-700/50 flex items-center gap-2 group"
          >
            <svg
              className="size-3.5 flex-shrink-0 text-neutral-500 group-hover:text-blue-400 transition-colors"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2}
            >
              <path strokeLinecap="round" strokeLinejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5" />
            </svg>
            <span>{question}</span>
          </button>
        ))}
      </div>
    </div>
  );
}

export function MessageBubble({ message, onFollowUpClick }: MessageBubbleProps) {
  const { user } = useUser();
  const isUser = message.role === 'user';

  // Get user initials or fallback to 'U'
  const userInitials = user ? getInitials(user.name) : 'U';

  // Parse follow-up questions from AI messages
  const { cleanContent, questions } = isUser
    ? { cleanContent: message.content, questions: [] }
    : parseFollowUpQuestions(message.content);

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
          // AI messages: render markdown with streamdown (without follow-up section)
          <div className="prose prose-invert prose-sm max-w-none">
            <Streamdown plugins={{ code }}>
              {cleanContent}
            </Streamdown>
          </div>
        )}

        {/* Sources with hover popovers */}
        {!isUser && message.sources && message.sources.length > 0 && (
          <SourcesList sources={message.sources} />
        )}

        {/* Follow-up questions as clickable buttons */}
        {!isUser && questions.length > 0 && (
          <FollowUpQuestions questions={questions} onQuestionClick={onFollowUpClick} />
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
