'use client';

import { cn } from '@/lib/utils/cn';
import { UserMenu } from '@/components/auth/UserMenu';

interface SidebarProps {
  currentSessionId: string | null;
  onSessionSelect: (id: string) => void;
  onNewChat: () => void;
}

export function Sidebar({ currentSessionId, onSessionSelect, onNewChat }: SidebarProps) {
  // TODO: Fetch sessions from API using useQuery
  const sessions: Array<{ id: string; title: string; updatedAt: string }> = [];

  return (
    <div className="flex h-full flex-col">
      {/* New Chat Button */}
      <div className="flex-shrink-0 p-3">
        <button
          onClick={onNewChat}
          className={cn(
            'flex w-full items-center gap-2 rounded-lg border border-neutral-700 px-3 py-2.5 text-sm font-medium text-neutral-200',
            'transition-colors hover:bg-neutral-800',
            !currentSessionId && 'bg-neutral-800'
          )}
        >
          <svg
            className="size-4"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={2}
          >
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
          </svg>
          New chat
        </button>
      </div>

      {/* Session List */}
      <div className="flex-1 overflow-y-auto px-3 pb-3">
        {sessions.length === 0 ? (
          <div className="py-8 text-center text-xs text-neutral-500">
            No conversations yet
          </div>
        ) : (
          <div className="space-y-1">
            {sessions.map((session) => (
              <button
                key={session.id}
                onClick={() => onSessionSelect(session.id)}
                className={cn(
                  'w-full rounded-lg px-3 py-2 text-left text-sm transition-colors',
                  session.id === currentSessionId
                    ? 'bg-neutral-800 text-neutral-100'
                    : 'text-neutral-400 hover:bg-neutral-800/50 hover:text-neutral-200'
                )}
              >
                <div className="truncate font-medium">{session.title}</div>
                <div className="mt-0.5 text-xs text-neutral-500">
                  {formatRelativeTime(session.updatedAt)}
                </div>
              </button>
            ))}
          </div>
        )}
      </div>

      {/* User Menu */}
      <div className="flex-shrink-0 border-t border-neutral-800 p-3">
        <UserMenu />
      </div>
    </div>
  );
}

function formatRelativeTime(dateString: string): string {
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffMins < 1) return 'Just now';
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;
  return date.toLocaleDateString();
}
