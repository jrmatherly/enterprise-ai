"use client";

import Link from "next/link";
import { useId, useState } from "react";
import {
  type KnowledgeBase,
  useCreateKnowledgeBase,
  useDeleteKnowledgeBase,
  useKnowledgeBases,
} from "@/lib/hooks/useKnowledgeBases";
import { cn } from "@/lib/utils/cn";

export default function KnowledgeBasesPage() {
  const { data: knowledgeBases, isLoading, error } = useKnowledgeBases();
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [kbToDelete, setKbToDelete] = useState<KnowledgeBase | null>(null);

  return (
    <div className="min-h-screen bg-neutral-950 text-neutral-100">
      {/* Header */}
      <header className="border-b border-neutral-800 bg-neutral-900/50 backdrop-blur-sm sticky top-0 z-10">
        <div className="mx-auto max-w-6xl px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link
              href="/"
              className="text-neutral-400 hover:text-neutral-200 transition-colors"
              aria-label="Go back to home"
            >
              <svg
                className="size-5"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={1.5}
                aria-hidden="true"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M10.5 19.5 3 12m0 0 7.5-7.5M3 12h18"
                />
              </svg>
            </Link>
            <div>
              <h1 className="text-xl font-semibold tracking-tight">
                Knowledge Bases
              </h1>
              <p className="text-sm text-neutral-500">
                Manage your document collections for AI-powered search
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={() => setShowCreateModal(true)}
            className="flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white transition-all hover:bg-blue-500 active:scale-[0.98]"
          >
            <svg
              className="size-4"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2}
              aria-hidden="true"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M12 4.5v15m7.5-7.5h-15"
              />
            </svg>
            New Knowledge Base
          </button>
        </div>
      </header>

      {/* Content */}
      <main className="mx-auto max-w-6xl px-6 py-8">
        {isLoading ? (
          <div className="flex flex-col items-center justify-center py-24">
            <div className="size-10 animate-spin rounded-full border-2 border-neutral-700 border-t-blue-500" />
            <p className="mt-4 text-sm text-neutral-500">
              Loading knowledge bases...
            </p>
          </div>
        ) : error ? (
          <div className="rounded-xl border border-red-900/50 bg-red-950/20 p-6 text-center">
            <p className="text-red-400">Failed to load knowledge bases</p>
          </div>
        ) : !knowledgeBases || knowledgeBases.length === 0 ? (
          <EmptyState onCreateClick={() => setShowCreateModal(true)} />
        ) : (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {knowledgeBases.map((kb) => (
              <KnowledgeBaseCard key={kb.id} kb={kb} onDelete={setKbToDelete} />
            ))}
          </div>
        )}
      </main>

      {/* Create Modal */}
      {showCreateModal && (
        <CreateKBModal onClose={() => setShowCreateModal(false)} />
      )}

      {/* Delete Confirmation Modal */}
      {kbToDelete && (
        <DeleteKBModal kb={kbToDelete} onClose={() => setKbToDelete(null)} />
      )}
    </div>
  );
}

function EmptyState({ onCreateClick }: { onCreateClick: () => void }) {
  return (
    <div className="flex flex-col items-center justify-center py-24 text-center">
      <div className="mb-6 flex size-20 items-center justify-center rounded-2xl bg-gradient-to-br from-neutral-800 to-neutral-900 ring-1 ring-neutral-700/50">
        <svg
          className="size-10 text-neutral-500"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={1}
          aria-hidden="true"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M20.25 6.375c0 2.278-3.694 4.125-8.25 4.125S3.75 8.653 3.75 6.375m16.5 0c0-2.278-3.694-4.125-8.25-4.125S3.75 4.097 3.75 6.375m16.5 0v11.25c0 2.278-3.694 4.125-8.25 4.125s-8.25-1.847-8.25-4.125V6.375m16.5 0v3.75m-16.5-3.75v3.75m16.5 0v3.75C20.25 16.153 16.556 18 12 18s-8.25-1.847-8.25-4.125v-3.75m16.5 0c0 2.278-3.694 4.125-8.25 4.125s-8.25-1.847-8.25-4.125"
          />
        </svg>
      </div>
      <h2 className="mb-2 text-xl font-semibold">No knowledge bases yet</h2>
      <p className="mb-8 max-w-sm text-neutral-500">
        Create a knowledge base to upload documents and enable AI-powered search
        across your content.
      </p>
      <button
        type="button"
        onClick={onCreateClick}
        className="flex items-center gap-2 rounded-lg bg-blue-600 px-5 py-2.5 text-sm font-medium text-white transition-all hover:bg-blue-500 active:scale-[0.98]"
      >
        <svg
          className="size-4"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={2}
          aria-hidden="true"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M12 4.5v15m7.5-7.5h-15"
          />
        </svg>
        Create your first knowledge base
      </button>
    </div>
  );
}

function KnowledgeBaseCard({
  kb,
  onDelete,
}: {
  kb: KnowledgeBase;
  onDelete: (kb: KnowledgeBase) => void;
}) {
  const scopeColors = {
    personal: "bg-emerald-500/10 text-emerald-400 ring-emerald-500/20",
    team: "bg-blue-500/10 text-blue-400 ring-blue-500/20",
    department: "bg-purple-500/10 text-purple-400 ring-purple-500/20",
    organization: "bg-amber-500/10 text-amber-400 ring-amber-500/20",
  };

  const handleDeleteClick = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    onDelete(kb);
  };

  return (
    <Link
      href={`/knowledge-bases/${kb.id}`}
      className="group relative rounded-xl border border-neutral-800 bg-neutral-900/50 p-5 transition-all hover:border-neutral-700 hover:bg-neutral-900"
    >
      {/* Delete Button */}
      <button
        type="button"
        onClick={handleDeleteClick}
        className="absolute right-3 top-3 rounded-md p-1.5 text-neutral-500 opacity-0 transition-all hover:bg-neutral-800 hover:text-red-400 group-hover:opacity-100"
        title="Delete knowledge base"
      >
        <svg
          className="size-4"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={2}
          aria-hidden="true"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="m14.74 9-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 0 1-2.244 2.077H8.084a2.25 2.25 0 0 1-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 0 0-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 0 1 3.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 0 0-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 0 0-7.5 0"
          />
        </svg>
      </button>

      {/* Scope Badge */}
      <div className="mb-4 flex items-center justify-between">
        <span
          className={cn(
            "rounded-full px-2.5 py-0.5 text-xs font-medium capitalize ring-1",
            scopeColors[kb.scope],
          )}
        >
          {kb.scope}
        </span>
        <span className="text-xs text-neutral-500 mr-6">
          {kb.document_count}{" "}
          {kb.document_count === 1 ? "document" : "documents"}
        </span>
      </div>

      {/* Title & Description */}
      <h3 className="mb-1 font-semibold text-neutral-100 group-hover:text-white transition-colors">
        {kb.name}
      </h3>
      {kb.description && (
        <p className="text-sm text-neutral-500 line-clamp-2">
          {kb.description}
        </p>
      )}

      {/* Footer */}
      <div className="mt-4 flex items-center justify-between text-xs text-neutral-600">
        <span>
          Updated {formatRelativeDate(kb.updated_at ?? kb.created_at)}
        </span>
        <svg
          className="size-4 text-neutral-600 transition-transform group-hover:translate-x-1 group-hover:text-neutral-400"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={2}
          aria-hidden="true"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M13.5 4.5 21 12m0 0-7.5 7.5M21 12H3"
          />
        </svg>
      </div>
    </Link>
  );
}

function CreateKBModal({ onClose }: { onClose: () => void }) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [systemPrompt, setSystemPrompt] = useState("");
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [scope, setScope] = useState<
    "personal" | "team" | "department" | "organization"
  >("personal");
  const createKB = useCreateKnowledgeBase();

  const nameId = useId();
  const descriptionId = useId();
  const systemPromptId = useId();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;

    try {
      await createKB.mutateAsync({
        name: name.trim(),
        description: description.trim() || undefined,
        scope,
        system_prompt: systemPrompt.trim() || undefined,
      });
      onClose();
    } catch (err) {
      console.error("Failed to create KB:", err);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <button
        type="button"
        className="absolute inset-0 cursor-default"
        onClick={onClose}
        aria-label="Close modal"
      />
      <div className="relative w-full max-w-md rounded-2xl border border-neutral-800 bg-neutral-900 p-6 shadow-2xl">
        <h2 className="mb-6 text-lg font-semibold">Create Knowledge Base</h2>

        <form onSubmit={handleSubmit} className="space-y-5">
          {/* Name */}
          <div>
            <label
              htmlFor={nameId}
              className="mb-1.5 block text-sm font-medium text-neutral-300"
            >
              Name
            </label>
            <input
              id={nameId}
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g., Product Documentation"
              className="w-full rounded-lg border border-neutral-700 bg-neutral-800 px-3 py-2 text-sm text-neutral-100 placeholder-neutral-500 outline-none transition-colors focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
            />
          </div>

          {/* Description */}
          <div>
            <label
              htmlFor={descriptionId}
              className="mb-1.5 block text-sm font-medium text-neutral-300"
            >
              Description <span className="text-neutral-500">(optional)</span>
            </label>
            <textarea
              id={descriptionId}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="What kind of documents will this contain?"
              rows={3}
              className="w-full rounded-lg border border-neutral-700 bg-neutral-800 px-3 py-2 text-sm text-neutral-100 placeholder-neutral-500 outline-none transition-colors focus:border-blue-500 focus:ring-1 focus:ring-blue-500 resize-none"
            />
          </div>

          {/* Scope */}
          <fieldset>
            <legend className="mb-1.5 block text-sm font-medium text-neutral-300">
              Scope
            </legend>
            <div className="grid grid-cols-2 gap-2">
              {(
                ["personal", "team", "department", "organization"] as const
              ).map((s) => (
                <button
                  key={s}
                  type="button"
                  onClick={() => setScope(s)}
                  className={cn(
                    "rounded-lg border px-3 py-2 text-sm font-medium capitalize transition-all",
                    scope === s
                      ? "border-blue-500 bg-blue-500/10 text-blue-400"
                      : "border-neutral-700 bg-neutral-800 text-neutral-400 hover:border-neutral-600",
                  )}
                >
                  {s}
                </button>
              ))}
            </div>
            <p className="mt-2 text-xs text-neutral-500">
              {scope === "personal" &&
                "Only you can access this knowledge base."}
              {scope === "team" &&
                "Your team members can access this knowledge base."}
              {scope === "department" &&
                "Your department can access this knowledge base."}
              {scope === "organization" &&
                "Everyone in your organization can access this knowledge base."}
            </p>
          </fieldset>

          {/* Advanced Settings */}
          <div className="border-t border-neutral-800 pt-4">
            <button
              type="button"
              onClick={() => setShowAdvanced(!showAdvanced)}
              className="flex items-center gap-2 text-sm text-neutral-400 hover:text-neutral-300 transition-colors"
            >
              <svg
                className={cn("size-4 transition-transform", showAdvanced && "rotate-90")}
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={2}
                aria-hidden="true"
              >
                <path strokeLinecap="round" strokeLinejoin="round" d="m9 5 7 7-7 7" />
              </svg>
              Advanced Settings
            </button>

            {showAdvanced && (
              <div className="mt-4">
                <label
                  htmlFor={systemPromptId}
                  className="mb-1.5 block text-sm font-medium text-neutral-300"
                >
                  Custom Instructions <span className="text-neutral-500">(optional)</span>
                </label>
                <textarea
                  id={systemPromptId}
                  value={systemPrompt}
                  onChange={(e) => setSystemPrompt(e.target.value)}
                  placeholder="e.g., 'SM' refers to Store Manager. Always cite policy numbers when referencing company policies."
                  rows={4}
                  className="w-full rounded-lg border border-neutral-700 bg-neutral-800 px-3 py-2 text-sm text-neutral-100 placeholder-neutral-500 outline-none transition-colors focus:border-blue-500 focus:ring-1 focus:ring-blue-500 resize-none"
                />
                <p className="mt-1.5 text-xs text-neutral-500">
                  Define acronyms, terminology, or instructions for how the AI should interact with this knowledge base.
                </p>
              </div>
            )}
          </div>

          {/* Actions */}
          <div className="flex gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 rounded-lg border border-neutral-700 bg-neutral-800 px-4 py-2 text-sm font-medium text-neutral-300 transition-colors hover:bg-neutral-700"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={!name.trim() || createKB.isPending}
              className="flex-1 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white transition-all hover:bg-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {createKB.isPending ? "Creating..." : "Create"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

function DeleteKBModal({
  kb,
  onClose,
}: {
  kb: KnowledgeBase;
  onClose: () => void;
}) {
  const deleteKB = useDeleteKnowledgeBase();

  const handleDelete = async () => {
    try {
      await deleteKB.mutateAsync(kb.id);
      onClose();
    } catch (err) {
      console.error("Failed to delete KB:", err);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <button
        type="button"
        className="absolute inset-0 cursor-default"
        onClick={onClose}
        aria-label="Close modal"
      />
      <div className="relative w-full max-w-md rounded-2xl border border-neutral-800 bg-neutral-900 p-6 shadow-2xl">
        <div className="mb-4 flex size-12 items-center justify-center rounded-full bg-red-500/10">
          <svg
            className="size-6 text-red-400"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={2}
            aria-hidden="true"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126ZM12 15.75h.007v.008H12v-.008Z"
            />
          </svg>
        </div>

        <h2 className="mb-2 text-lg font-semibold">Delete Knowledge Base</h2>
        <p className="mb-2 text-neutral-400">
          Are you sure you want to delete{" "}
          <span className="font-medium text-neutral-200">{kb.name}</span>?
        </p>
        <p className="mb-6 text-sm text-neutral-500">
          This will permanently delete the knowledge base and all{" "}
          {kb.document_count}{" "}
          {kb.document_count === 1 ? "document" : "documents"} within it. This
          action cannot be undone.
        </p>

        <div className="flex gap-3">
          <button
            type="button"
            onClick={onClose}
            className="flex-1 rounded-lg border border-neutral-700 bg-neutral-800 px-4 py-2 text-sm font-medium text-neutral-300 transition-colors hover:bg-neutral-700"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={handleDelete}
            disabled={deleteKB.isPending}
            className="flex-1 rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white transition-all hover:bg-red-500 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {deleteKB.isPending ? "Deleting..." : "Delete"}
          </button>
        </div>
      </div>
    </div>
  );
}

function formatRelativeDate(dateString: string | null | undefined): string {
  if (!dateString) return "Unknown";

  const date = new Date(dateString);
  if (Number.isNaN(date.getTime())) return "Unknown";

  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffDays === 0) return "today";
  if (diffDays === 1) return "yesterday";
  if (diffDays < 7) return `${diffDays} days ago`;
  if (diffDays < 30) return `${Math.floor(diffDays / 7)} weeks ago`;
  return date.toLocaleDateString();
}
