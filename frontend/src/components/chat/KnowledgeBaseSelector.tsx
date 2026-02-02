"use client";

import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import {
  type KnowledgeBase,
  useKnowledgeBases,
} from "@/lib/hooks/useKnowledgeBases";
import { cn } from "@/lib/utils/cn";

interface KnowledgeBaseSelectorProps {
  selectedIds: string[];
  onSelectionChange: (ids: string[]) => void;
  disabled?: boolean;
}

export function KnowledgeBaseSelector({
  selectedIds,
  onSelectionChange,
  disabled,
}: KnowledgeBaseSelectorProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [dropdownPosition, setDropdownPosition] = useState({ top: 0, left: 0 });
  const buttonRef = useRef<HTMLButtonElement>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const { data: knowledgeBases, isLoading } = useKnowledgeBases();

  // Update dropdown position when opened
  useEffect(() => {
    if (isOpen && buttonRef.current) {
      const rect = buttonRef.current.getBoundingClientRect();
      setDropdownPosition({
        top: rect.top - 8, // Position above the button with 8px gap
        left: rect.left,
      });
    }
  }, [isOpen]);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(event.target as Node) &&
        buttonRef.current &&
        !buttonRef.current.contains(event.target as Node)
      ) {
        setIsOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  // Close on escape
  useEffect(() => {
    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") setIsOpen(false);
    };
    document.addEventListener("keydown", handleEscape);
    return () => document.removeEventListener("keydown", handleEscape);
  }, []);

  const toggleKB = (kbId: string) => {
    if (selectedIds.includes(kbId)) {
      onSelectionChange(selectedIds.filter((id) => id !== kbId));
    } else {
      onSelectionChange([...selectedIds, kbId]);
    }
  };

  const selectedKBs =
    knowledgeBases?.filter((kb) => selectedIds.includes(kb.id)) || [];
  const hasSelection = selectedKBs.length > 0;

  return (
    <>
      {/* Trigger Button */}
      <button
        ref={buttonRef}
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        disabled={disabled || isLoading}
        className={cn(
          "flex items-center gap-2 rounded-full px-3 py-1.5 text-sm font-medium transition-all",
          "border border-neutral-700 hover:border-neutral-600",
          hasSelection
            ? "bg-blue-600/10 text-blue-400 border-blue-600/30 hover:border-blue-500/50"
            : "bg-neutral-800/50 text-neutral-400 hover:text-neutral-300",
          "disabled:opacity-50 disabled:cursor-not-allowed",
        )}
      >
        {/* Knowledge Base Icon */}
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
            d="M20.25 6.375c0 2.278-3.694 4.125-8.25 4.125S3.75 8.653 3.75 6.375m16.5 0c0-2.278-3.694-4.125-8.25-4.125S3.75 4.097 3.75 6.375m16.5 0v11.25c0 2.278-3.694 4.125-8.25 4.125s-8.25-1.847-8.25-4.125V6.375m16.5 0v3.75m-16.5-3.75v3.75m16.5 0v3.75C20.25 16.153 16.556 18 12 18s-8.25-1.847-8.25-4.125v-3.75m16.5 0c0 2.278-3.694 4.125-8.25 4.125s-8.25-1.847-8.25-4.125"
          />
        </svg>

        <span>
          {hasSelection
            ? selectedKBs.length === 1
              ? selectedKBs[0].name
              : `${selectedKBs.length} Knowledge Bases`
            : "Knowledge"}
        </span>

        {/* Chevron */}
        <svg
          className={cn("size-3 transition-transform", isOpen && "rotate-180")}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={2}
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="m19.5 8.25-7.5 7.5-7.5-7.5"
          />
        </svg>
      </button>

      {/* Dropdown Menu - rendered in portal */}
      {isOpen &&
        typeof document !== "undefined" &&
        createPortal(
          <div
            ref={dropdownRef}
            className="fixed w-72 rounded-xl border border-neutral-700 bg-neutral-900 p-2 shadow-2xl animate-in fade-in slide-in-from-bottom-2 duration-150"
            style={{
              top: dropdownPosition.top,
              left: dropdownPosition.left,
              transform: "translateY(-100%)",
              zIndex: 9999,
            }}
          >
            {/* Header */}
            <div className="px-2 py-1.5 mb-1">
              <h3 className="text-xs font-semibold uppercase tracking-wider text-neutral-500">
                Search Knowledge Bases
              </h3>
            </div>

            {/* KB List */}
            <div className="max-h-64 overflow-y-auto">
              {isLoading ? (
                <div className="flex items-center justify-center py-6">
                  <div className="size-5 animate-spin rounded-full border-2 border-neutral-600 border-t-blue-500" />
                </div>
              ) : !knowledgeBases || knowledgeBases.length === 0 ? (
                <div className="py-6 text-center">
                  <p className="text-sm text-neutral-500">
                    No knowledge bases available
                  </p>
                  <a
                    href="/knowledge-bases"
                    className="mt-2 inline-block text-xs text-blue-400 hover:text-blue-300"
                    onClick={() => setIsOpen(false)}
                  >
                    Create one →
                  </a>
                </div>
              ) : (
                <div className="space-y-0.5">
                  {knowledgeBases.map((kb) => (
                    <KBOption
                      key={kb.id}
                      kb={kb}
                      selected={selectedIds.includes(kb.id)}
                      onToggle={() => toggleKB(kb.id)}
                    />
                  ))}
                </div>
              )}
            </div>

            {/* Footer */}
            {hasSelection && (
              <div className="mt-2 pt-2 border-t border-neutral-800">
                <button
                  onClick={() => {
                    onSelectionChange([]);
                    setIsOpen(false);
                  }}
                  className="w-full rounded-lg px-3 py-1.5 text-xs text-neutral-500 hover:text-neutral-300 hover:bg-neutral-800 transition-colors"
                >
                  Clear selection
                </button>
              </div>
            )}
          </div>,
          document.body,
        )}
    </>
  );
}

function KBOption({
  kb,
  selected,
  onToggle,
}: {
  kb: KnowledgeBase;
  selected: boolean;
  onToggle: () => void;
}) {
  const scopeColors: Record<string, string> = {
    personal: "text-emerald-400",
    team: "text-blue-400",
    department: "text-purple-400",
    organization: "text-amber-400",
  };

  return (
    <button
      onClick={onToggle}
      className={cn(
        "flex w-full items-center gap-3 rounded-lg px-2 py-2 text-left transition-colors",
        selected
          ? "bg-blue-600/10 text-neutral-100"
          : "hover:bg-neutral-800 text-neutral-300",
      )}
    >
      {/* Checkbox */}
      <div
        className={cn(
          "flex size-4 items-center justify-center rounded border transition-colors",
          selected
            ? "border-blue-500 bg-blue-600"
            : "border-neutral-600 bg-neutral-800",
        )}
      >
        {selected && (
          <svg
            className="size-3 text-white"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={3}
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="m4.5 12.75 6 6 9-13.5"
            />
          </svg>
        )}
      </div>

      {/* KB Info */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium truncate">{kb.name}</span>
          <span className={cn("text-[10px] uppercase", scopeColors[kb.scope])}>
            {kb.scope}
          </span>
        </div>
        <p className="text-xs text-neutral-500 truncate">
          {kb.document_count} {kb.document_count === 1 ? "doc" : "docs"}
        </p>
      </div>
    </button>
  );
}

/**
 * Selected KB Pills - shows selected knowledge bases as removable chips
 */
export function SelectedKBPills({
  selectedIds,
  onRemove,
}: {
  selectedIds: string[];
  onRemove: (id: string) => void;
}) {
  const { data: knowledgeBases } = useKnowledgeBases();
  const selectedKBs =
    knowledgeBases?.filter((kb) => selectedIds.includes(kb.id)) || [];

  if (selectedKBs.length === 0) return null;

  return (
    <div className="flex flex-wrap gap-1.5">
      {selectedKBs.map((kb) => (
        <div
          key={kb.id}
          className="flex items-center gap-1.5 rounded-full bg-blue-600/10 border border-blue-600/20 px-2.5 py-1 text-xs text-blue-400"
        >
          <span className="max-w-[120px] truncate">{kb.name}</span>
          <button
            onClick={() => onRemove(kb.id)}
            className="rounded-full p-0.5 hover:bg-blue-600/20 transition-colors"
          >
            <svg
              className="size-3"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M6 18 18 6M6 6l12 12"
              />
            </svg>
          </button>
        </div>
      ))}
    </div>
  );
}
