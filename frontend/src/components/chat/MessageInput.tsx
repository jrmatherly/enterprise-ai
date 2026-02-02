"use client";

import { useCallback, useRef, useState } from "react";
import { cn } from "@/lib/utils/cn";
import {
  KnowledgeBaseSelector,
  SelectedKBPills,
} from "./KnowledgeBaseSelector";

interface MessageInputProps {
  onSend: (message: string, knowledgeBaseIds?: string[]) => void;
  disabled?: boolean;
  placeholder?: string;
  selectedKBIds?: string[];
  onKBSelectionChange?: (ids: string[]) => void;
}

export function MessageInput({
  onSend,
  disabled,
  placeholder,
  selectedKBIds: controlledKBIds,
  onKBSelectionChange,
}: MessageInputProps) {
  const [value, setValue] = useState("");
  // Use controlled state if provided, otherwise manage internally
  const [internalKBIds, setInternalKBIds] = useState<string[]>([]);
  const selectedKBIds = controlledKBIds ?? internalKBIds;
  const setSelectedKBIds = onKBSelectionChange ?? setInternalKBIds;
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleSubmit = useCallback(() => {
    const trimmed = value.trim();
    if (trimmed && !disabled) {
      onSend(trimmed, selectedKBIds.length > 0 ? selectedKBIds : undefined);
      setValue("");
      // Reset textarea height
      if (textareaRef.current) {
        textareaRef.current.style.height = "auto";
      }
    }
  }, [value, disabled, onSend, selectedKBIds]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handleInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setValue(e.target.value);
    // Auto-resize textarea
    const textarea = e.target;
    textarea.style.height = "auto";
    textarea.style.height = `${Math.min(textarea.scrollHeight, 200)}px`;
  };

  const removeKB = (id: string) => {
    setSelectedKBIds(selectedKBIds.filter((kbId) => kbId !== id));
  };

  return (
    <div className="space-y-3">
      {/* Selected KB Pills */}
      {selectedKBIds.length > 0 && (
        <SelectedKBPills selectedIds={selectedKBIds} onRemove={removeKB} />
      )}

      {/* Main Input Container */}
      <div className="rounded-2xl border border-neutral-700 bg-neutral-800/50 transition-colors focus-within:border-neutral-600 focus-within:bg-neutral-800">
        {/* Text Input Area */}
        <div className="relative">
          <textarea
            ref={textareaRef}
            value={value}
            onChange={handleInput}
            onKeyDown={handleKeyDown}
            placeholder={placeholder}
            disabled={disabled}
            rows={1}
            className={cn(
              "w-full resize-none bg-transparent px-4 pt-3 pb-2 pr-14 text-sm text-neutral-100 placeholder:text-neutral-500",
              "focus:outline-none",
              "disabled:cursor-not-allowed disabled:opacity-50",
            )}
            style={{ maxHeight: "200px" }}
          />

          {/* Send Button */}
          <button
            type="button"
            onClick={handleSubmit}
            disabled={disabled || !value.trim()}
            className={cn(
              "absolute right-2 top-2 flex size-9 items-center justify-center rounded-lg transition-all",
              value.trim() && !disabled
                ? "bg-blue-600 text-white hover:bg-blue-500 scale-100"
                : "text-neutral-500 hover:text-neutral-400 scale-95 opacity-70",
            )}
            aria-label="Send message"
          >
            <svg
              className="size-5"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2}
              aria-hidden="true"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M6 12 3.269 3.125A59.769 59.769 0 0 1 21.485 12 59.768 59.768 0 0 1 3.27 20.875L5.999 12Zm0 0h7.5"
              />
            </svg>
          </button>
        </div>

        {/* Action Bar */}
        <div className="flex items-center gap-2 px-3 pb-2">
          {/* Knowledge Base Selector */}
          <KnowledgeBaseSelector
            selectedIds={selectedKBIds}
            onSelectionChange={setSelectedKBIds}
            disabled={disabled}
          />

          {/* Divider */}
          <div className="h-4 w-px bg-neutral-700" />

          {/* Attachment Button (placeholder for future) */}
          <button
            type="button"
            disabled={disabled}
            className={cn(
              "flex items-center gap-1.5 rounded-full px-2.5 py-1.5 text-sm font-medium transition-all",
              "border border-neutral-700 hover:border-neutral-600",
              "bg-neutral-800/50 text-neutral-400 hover:text-neutral-300",
              "disabled:opacity-50 disabled:cursor-not-allowed",
            )}
            title="Attach files (coming soon)"
          >
            <svg
              className="size-4"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={1.5}
              aria-hidden="true"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="m18.375 12.739-7.693 7.693a4.5 4.5 0 0 1-6.364-6.364l10.94-10.94A3 3 0 1 1 19.5 7.372L8.552 18.32m.009-.01-.01.01m5.699-9.941-7.81 7.81a1.5 1.5 0 0 0 2.112 2.13"
              />
            </svg>
            <span>Attach</span>
          </button>

          {/* Spacer */}
          <div className="flex-1" />

          {/* Character hint */}
          <span className="text-xs text-neutral-600">
            Shift+Enter for new line
          </span>
        </div>
      </div>
    </div>
  );
}
