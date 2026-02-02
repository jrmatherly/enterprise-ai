'use client';

import { useEffect, useRef, useState } from 'react';
import { UserMenu } from '@/components/auth/UserMenu';
import { useDeleteSession, useSessions, useUpdateSession } from '@/lib/hooks/useSessions';
import { cn } from '@/lib/utils/cn';

// Maximum number of conversations to display/retain
const MAX_SESSIONS = 50;

interface SidebarProps {
  currentSessionId: string | null;
  onSessionSelect: (id: string) => void;
  onNewChat: () => void;
}

export function Sidebar({ currentSessionId, onSessionSelect, onNewChat }: SidebarProps) {
  const { data: sessions, isLoading, error } = useSessions(MAX_SESSIONS);
  const deleteSession = useDeleteSession();
  const updateSession = useUpdateSession();
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editTitle, setEditTitle] = useState('');
  const editInputRef = useRef<HTMLInputElement>(null);

  // Focus input when editing starts
  useEffect(() => {
    if (editingId && editInputRef.current) {
      editInputRef.current.focus();
      editInputRef.current.select();
    }
  }, [editingId]);

  const handleDelete = async (e: React.MouseEvent, sessionId: string) => {
    e.stopPropagation();
    if (deletingId) return;
    
    setDeletingId(sessionId);
    try {
      await deleteSession.mutateAsync(sessionId);
      if (sessionId === currentSessionId) {
        onNewChat();
      }
    } catch (err) {
      console.error('Failed to delete session:', err);
    } finally {
      setDeletingId(null);
    }
  };

  const handleStartEdit = (e: React.MouseEvent, sessionId: string, currentTitle: string | null) => {
    e.stopPropagation();
    setEditingId(sessionId);
    setEditTitle(currentTitle || '');
  };

  const handleSaveEdit = async (sessionId: string) => {
    if (!editTitle.trim()) {
      setEditingId(null);
      return;
    }
    
    try {
      await updateSession.mutateAsync({ sessionId, title: editTitle.trim() });
    } catch (err) {
      console.error('Failed to rename session:', err);
    } finally {
      setEditingId(null);
    }
  };

  const handleEditKeyDown = (e: React.KeyboardEvent, sessionId: string) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      handleSaveEdit(sessionId);
    } else if (e.key === 'Escape') {
      setEditingId(null);
    }
  };

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
      <div className="flex-1 overflow-y-auto overflow-x-hidden px-3 pb-3">
        {isLoading ? (
          <div className="flex items-center justify-center py-8">
            <div className="size-5 animate-spin rounded-full border-2 border-neutral-600 border-t-neutral-300" />
          </div>
        ) : error ? (
          <div className="py-8 text-center text-xs text-red-400">
            Failed to load sessions
          </div>
        ) : !sessions || sessions.length === 0 ? (
          <div className="py-8 text-center text-xs text-neutral-500">
            No conversations yet
          </div>
        ) : (
          <div className="space-y-1">
            {sessions.map((session) => (
              <div
                key={session.id}
                className={cn(
                  'group relative flex items-center rounded-lg transition-colors',
                  session.id === currentSessionId
                    ? 'bg-neutral-800 text-neutral-100'
                    : 'text-neutral-400 hover:bg-neutral-800/50 hover:text-neutral-200'
                )}
              >
                {editingId === session.id ? (
                  /* Edit Mode */
                  <div className="flex-1 px-3 py-2">
                    <input
                      ref={editInputRef}
                      type="text"
                      value={editTitle}
                      onChange={(e) => setEditTitle(e.target.value)}
                      onKeyDown={(e) => handleEditKeyDown(e, session.id)}
                      onBlur={() => handleSaveEdit(session.id)}
                      className="w-full rounded bg-neutral-700 px-2 py-1 text-sm text-neutral-100 outline-none ring-1 ring-blue-500"
                      placeholder="Conversation name"
                    />
                  </div>
                ) : (
                  /* View Mode */
                  <>
                    <button
                      onClick={() => onSessionSelect(session.id)}
                      className="min-w-0 flex-1 px-3 py-2 text-left text-sm"
                    >
                      <div className="truncate font-medium">
                        {session.title || 'New conversation'}
                      </div>
                      <div className="mt-0.5 text-xs text-neutral-500">
                        {formatRelativeTime(session.updated_at)}
                      </div>
                    </button>
                    
                    {/* Action Buttons - appear on hover */}
                    <div className="absolute right-2 flex gap-1 opacity-0 transition-opacity group-hover:opacity-100">
                      {/* Edit Button */}
                      <button
                        onClick={(e) => handleStartEdit(e, session.id, session.title)}
                        className="rounded p-1 hover:bg-neutral-700"
                        title="Rename conversation"
                      >
                        <svg
                          className="size-4 text-neutral-400 hover:text-neutral-200"
                          fill="none"
                          viewBox="0 0 24 24"
                          stroke="currentColor"
                          strokeWidth={2}
                        >
                          <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            d="m16.862 4.487 1.687-1.688a1.875 1.875 0 1 1 2.652 2.652L10.582 16.07a4.5 4.5 0 0 1-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 0 1 1.13-1.897l8.932-8.931Zm0 0L19.5 7.125M18 14v4.75A2.25 2.25 0 0 1 15.75 21H5.25A2.25 2.25 0 0 1 3 18.75V8.25A2.25 2.25 0 0 1 5.25 6H10"
                          />
                        </svg>
                      </button>
                      
                      {/* Delete Button */}
                      <button
                        onClick={(e) => handleDelete(e, session.id)}
                        disabled={deletingId === session.id}
                        className={cn(
                          'rounded p-1 hover:bg-neutral-700',
                          'disabled:cursor-not-allowed disabled:opacity-50'
                        )}
                        title="Delete conversation"
                      >
                        {deletingId === session.id ? (
                          <div className="size-4 animate-spin rounded-full border-2 border-neutral-600 border-t-neutral-300" />
                        ) : (
                          <svg
                            className="size-4 text-neutral-400 hover:text-red-400"
                            fill="none"
                            viewBox="0 0 24 24"
                            stroke="currentColor"
                            strokeWidth={2}
                          >
                            <path
                              strokeLinecap="round"
                              strokeLinejoin="round"
                              d="M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 01-2.244 2.077H8.084a2.25 2.25 0 01-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 00-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 013.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 00-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 00-7.5 0"
                            />
                          </svg>
                        )}
                      </button>
                    </div>
                  </>
                )}
              </div>
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

function formatRelativeTime(dateString: string | null | undefined): string {
  if (!dateString) return 'Unknown';
  
  const date = new Date(dateString);
  
  // Check for invalid date
  if (Number.isNaN(date.getTime())) return 'Unknown';
  
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
