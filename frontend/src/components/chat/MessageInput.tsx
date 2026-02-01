'use client';

import { useState, useRef, useCallback } from 'react';
import { cn } from '@/lib/utils/cn';

interface MessageInputProps {
  onSend: (message: string) => void;
  disabled?: boolean;
  placeholder?: string;
}

export function MessageInput({ onSend, disabled, placeholder }: MessageInputProps) {
  const [value, setValue] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleSubmit = useCallback(() => {
    const trimmed = value.trim();
    if (trimmed && !disabled) {
      onSend(trimmed);
      setValue('');
      // Reset textarea height
      if (textareaRef.current) {
        textareaRef.current.style.height = 'auto';
      }
    }
  }, [value, disabled, onSend]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handleInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setValue(e.target.value);
    // Auto-resize textarea
    const textarea = e.target;
    textarea.style.height = 'auto';
    textarea.style.height = `${Math.min(textarea.scrollHeight, 200)}px`;
  };

  return (
    <div className="flex items-end gap-2">
      <div className="relative flex-1">
        <textarea
          ref={textareaRef}
          value={value}
          onChange={handleInput}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          disabled={disabled}
          rows={1}
          className={cn(
            'w-full resize-none rounded-xl border border-neutral-700 bg-neutral-800 px-4 py-3 pr-12 text-sm text-neutral-100 placeholder:text-neutral-500',
            'focus:border-neutral-600 focus:outline-none focus:ring-1 focus:ring-neutral-600',
            'disabled:cursor-not-allowed disabled:opacity-50',
            'transition-colors'
          )}
          style={{ maxHeight: '200px' }}
        />
      </div>
      
      <button
        onClick={handleSubmit}
        disabled={disabled || !value.trim()}
        className={cn(
          'flex size-11 flex-shrink-0 items-center justify-center rounded-xl transition-colors',
          value.trim() && !disabled
            ? 'bg-blue-600 text-white hover:bg-blue-500'
            : 'bg-neutral-800 text-neutral-500 cursor-not-allowed'
        )}
        aria-label="Send message"
      >
        <svg
          className="size-5"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={2}
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M6 12 3.269 3.125A59.769 59.769 0 0 1 21.485 12 59.768 59.768 0 0 1 3.27 20.875L5.999 12Zm0 0h7.5"
          />
        </svg>
      </button>
    </div>
  );
}
