'use client';

import { code } from '@streamdown/code';
import { Streamdown } from 'streamdown';
import { getInitials, useUser } from '@/lib/contexts/UserContext';
import type { Message } from '@/lib/types';
import { cn } from '@/lib/utils/cn';

interface MessageBubbleProps {
  message: Message;
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
