import { cn } from '@/lib/utils/cn';
import type { Message } from '@/lib/types';

interface MessageBubbleProps {
  message: Message;
}

export function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === 'user';
  
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
        {isUser ? 'U' : 'AI'}
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
        <div className="whitespace-pre-wrap text-sm leading-relaxed text-pretty">
          {message.content}
        </div>
        
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
  if (isNaN(date.getTime())) {
    return '';
  }
  
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}
