'use client';

import { useState, useRef, useEffect } from 'react';
import { useSession, signOutAndRedirect } from '@/lib/auth-client';
import { cn } from '@/lib/utils/cn';

export function UserMenu() {
  const { data: session, isPending } = useSession();
  const [isOpen, setIsOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  // Close menu when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  if (isPending) {
    return (
      <div className="flex size-8 items-center justify-center rounded-full bg-neutral-700">
        <div className="size-4 animate-spin rounded-full border-2 border-neutral-400 border-t-transparent" />
      </div>
    );
  }

  if (!session?.user) {
    return null;
  }

  const user = session.user;
  const initials = user.name
    ? user.name
        .split(' ')
        .map((n) => n[0])
        .join('')
        .toUpperCase()
        .slice(0, 2)
    : user.email?.[0]?.toUpperCase() || 'U';

  return (
    <div className="relative" ref={menuRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-3 rounded-lg px-2 py-2 transition-colors hover:bg-neutral-800"
      >
        {user.image ? (
          <img
            src={user.image}
            alt={user.name || 'User'}
            className="size-8 rounded-full object-cover"
          />
        ) : (
          <div className="flex size-8 items-center justify-center rounded-full bg-blue-600 text-xs font-medium text-white">
            {initials}
          </div>
        )}
        <div className="min-w-0 flex-1 text-left">
          <div className="truncate text-sm font-medium text-neutral-200">
            {user.name || 'User'}
          </div>
          <div className="truncate text-xs text-neutral-500">
            {user.email}
          </div>
        </div>
        <svg
          className={cn(
            'size-4 text-neutral-400 transition-transform',
            isOpen && 'rotate-180'
          )}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={2}
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="m19.5 8.25-7.5 7.5-7.5-7.5" />
        </svg>
      </button>

      {isOpen && (
        <div className="absolute bottom-full left-0 right-0 mb-2 rounded-lg border border-neutral-700 bg-neutral-800 py-1 shadow-lg">
          <div className="border-b border-neutral-700 px-3 py-2">
            <div className="text-sm font-medium text-neutral-200">{user.name}</div>
            <div className="text-xs text-neutral-400">{user.email}</div>
          </div>
          <button
            onClick={() => signOutAndRedirect('/login')}
            className="flex w-full items-center gap-2 px-3 py-2 text-sm text-neutral-300 transition-colors hover:bg-neutral-700"
          >
            <svg
              className="size-4"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={1.5}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M8.25 9V5.25A2.25 2.25 0 0 1 10.5 3h6a2.25 2.25 0 0 1 2.25 2.25v13.5A2.25 2.25 0 0 1 16.5 21h-6a2.25 2.25 0 0 1-2.25-2.25V15m-3 0-3-3m0 0 3-3m-3 3H15"
              />
            </svg>
            Sign out
          </button>
        </div>
      )}
    </div>
  );
}
