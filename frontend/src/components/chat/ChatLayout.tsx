'use client';

import { useState } from 'react';
import { Sidebar } from './Sidebar';
import { ChatArea } from './ChatArea';
import { cn } from '@/lib/utils/cn';

export function ChatLayout() {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);

  return (
    <div className="flex h-dvh bg-neutral-950 text-neutral-100">
      {/* Sidebar */}
      <aside
        className={cn(
          'flex-shrink-0 border-r border-neutral-800 bg-neutral-900 transition-[width] duration-200 ease-out',
          sidebarOpen ? 'w-64' : 'w-0 overflow-hidden'
        )}
      >
        <Sidebar
          currentSessionId={currentSessionId}
          onSessionSelect={setCurrentSessionId}
          onNewChat={() => setCurrentSessionId(null)}
        />
      </aside>

      {/* Main Chat Area */}
      <main className="flex flex-1 flex-col min-w-0">
        {/* Header */}
        <header className="flex h-14 flex-shrink-0 items-center gap-3 border-b border-neutral-800 px-4">
          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="flex size-9 items-center justify-center rounded-md text-neutral-400 transition-colors hover:bg-neutral-800 hover:text-neutral-100"
            aria-label={sidebarOpen ? 'Close sidebar' : 'Open sidebar'}
          >
            <svg
              className="size-5"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={1.5}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25h16.5"
              />
            </svg>
          </button>
          <div className="flex-1">
            <h1 className="text-sm font-medium text-neutral-200">
              {currentSessionId ? 'Chat Session' : 'New Conversation'}
            </h1>
          </div>
        </header>

        {/* Chat Content */}
        <ChatArea
          sessionId={currentSessionId}
          onSessionCreated={setCurrentSessionId}
        />
      </main>
    </div>
  );
}
