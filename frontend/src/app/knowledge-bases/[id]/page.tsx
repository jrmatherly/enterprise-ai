"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useCallback, useState } from "react";
import {
	type Document,
	useDeleteDocument,
	useDeleteKnowledgeBase,
	useDocuments,
	useKnowledgeBase,
	useUploadDocument,
} from "@/lib/hooks/useKnowledgeBases";
import { cn } from "@/lib/utils/cn";

export default function KnowledgeBaseDetailPage() {
	const params = useParams();
	const router = useRouter();
	const kbId = params.id as string;

	const { data: kb, isLoading: kbLoading } = useKnowledgeBase(kbId);
	const { data: documents, isLoading: docsLoading } = useDocuments(kbId);
	const deleteKB = useDeleteKnowledgeBase();
	const [showDeleteModal, setShowDeleteModal] = useState(false);

	const handleDeleteKB = async () => {
		try {
			await deleteKB.mutateAsync(kbId);
			router.push("/knowledge-bases");
		} catch (err) {
			console.error("Failed to delete KB:", err);
		}
	};

	if (kbLoading) {
		return (
			<div className="flex min-h-screen items-center justify-center bg-neutral-950">
				<div className="flex flex-col items-center">
					<div className="size-10 animate-spin rounded-full border-2 border-neutral-700 border-t-blue-500" />
					<p className="mt-4 text-sm text-neutral-500">Loading...</p>
				</div>
			</div>
		);
	}

	if (!kb) {
		return (
			<div className="flex min-h-screen items-center justify-center bg-neutral-950">
				<div className="text-center">
					<h1 className="text-xl font-semibold text-neutral-100">
						Knowledge Base Not Found
					</h1>
					<p className="mt-2 text-neutral-500">
						The knowledge base you're looking for doesn't exist.
					</p>
					<Link
						href="/knowledge-bases"
						className="mt-6 inline-block rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-500"
					>
						Back to Knowledge Bases
					</Link>
				</div>
			</div>
		);
	}

	return (
		<div className="min-h-screen bg-neutral-950 text-neutral-100">
			{/* Header */}
			<header className="border-b border-neutral-800 bg-neutral-900/50 backdrop-blur-sm sticky top-0 z-10">
				<div className="mx-auto max-w-6xl px-6 py-4">
					<div className="flex items-center gap-4">
						<Link
							href="/knowledge-bases"
							className="text-neutral-400 hover:text-neutral-200 transition-colors"
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
									d="M10.5 19.5 3 12m0 0 7.5-7.5M3 12h18"
								/>
							</svg>
						</Link>
						<div className="flex-1">
							<div className="flex items-center gap-3">
								<h1 className="text-xl font-semibold tracking-tight">
									{kb.name}
								</h1>
								<ScopeBadge scope={kb.scope} />
							</div>
							{kb.description && (
								<p className="mt-1 text-sm text-neutral-500">
									{kb.description}
								</p>
							)}
						</div>
						<button
							onClick={() => setShowDeleteModal(true)}
							className="rounded-lg border border-neutral-700 bg-neutral-800 px-3 py-2 text-sm font-medium text-neutral-400 transition-all hover:border-red-800 hover:bg-red-950/50 hover:text-red-400"
						>
							<svg
								className="size-4"
								fill="none"
								viewBox="0 0 24 24"
								stroke="currentColor"
								strokeWidth={2}
							>
								<path
									strokeLinecap="round"
									strokeLinejoin="round"
									d="m14.74 9-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 0 1-2.244 2.077H8.084a2.25 2.25 0 0 1-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 0 0-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 0 1 3.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 0 0-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 0 0-7.5 0"
								/>
							</svg>
						</button>
					</div>
				</div>
			</header>

			{/* Delete KB Modal */}
			{showDeleteModal && (
				<div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
					<div
						className="absolute inset-0"
						onClick={() => setShowDeleteModal(false)}
					/>
					<div className="relative w-full max-w-md rounded-2xl border border-neutral-800 bg-neutral-900 p-6 shadow-2xl">
						<div className="mb-4 flex size-12 items-center justify-center rounded-full bg-red-500/10">
							<svg
								className="size-6 text-red-400"
								fill="none"
								viewBox="0 0 24 24"
								stroke="currentColor"
								strokeWidth={2}
							>
								<path
									strokeLinecap="round"
									strokeLinejoin="round"
									d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126ZM12 15.75h.007v.008H12v-.008Z"
								/>
							</svg>
						</div>

						<h2 className="mb-2 text-lg font-semibold">
							Delete Knowledge Base
						</h2>
						<p className="mb-2 text-neutral-400">
							Are you sure you want to delete{" "}
							<span className="font-medium text-neutral-200">{kb.name}</span>?
						</p>
						<p className="mb-6 text-sm text-neutral-500">
							This will permanently delete the knowledge base and all{" "}
							{kb.document_count}{" "}
							{kb.document_count === 1 ? "document" : "documents"} within it.
							This action cannot be undone.
						</p>

						<div className="flex gap-3">
							<button
								type="button"
								onClick={() => setShowDeleteModal(false)}
								className="flex-1 rounded-lg border border-neutral-700 bg-neutral-800 px-4 py-2 text-sm font-medium text-neutral-300 transition-colors hover:bg-neutral-700"
							>
								Cancel
							</button>
							<button
								onClick={handleDeleteKB}
								disabled={deleteKB.isPending}
								className="flex-1 rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white transition-all hover:bg-red-500 disabled:opacity-50 disabled:cursor-not-allowed"
							>
								{deleteKB.isPending ? "Deleting..." : "Delete"}
							</button>
						</div>
					</div>
				</div>
			)}

			{/* Content */}
			<main className="mx-auto max-w-6xl px-6 py-8">
				{/* Upload Section */}
				<DocumentUploadZone kbId={kbId} />

				{/* Documents Section */}
				<div className="mt-8">
					<div className="mb-4 flex items-center justify-between">
						<h2 className="text-lg font-semibold">Documents</h2>
						<span className="text-sm text-neutral-500">
							{documents?.length || 0}{" "}
							{documents?.length === 1 ? "document" : "documents"}
						</span>
					</div>

					{docsLoading ? (
						<div className="flex items-center justify-center py-12">
							<div className="size-8 animate-spin rounded-full border-2 border-neutral-700 border-t-blue-500" />
						</div>
					) : !documents || documents.length === 0 ? (
						<div className="rounded-xl border border-dashed border-neutral-800 py-12 text-center">
							<svg
								className="mx-auto size-12 text-neutral-700"
								fill="none"
								viewBox="0 0 24 24"
								stroke="currentColor"
								strokeWidth={1}
							>
								<path
									strokeLinecap="round"
									strokeLinejoin="round"
									d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z"
								/>
							</svg>
							<p className="mt-4 text-neutral-500">No documents yet</p>
							<p className="text-sm text-neutral-600">
								Upload files above to get started
							</p>
						</div>
					) : (
						<DocumentTable documents={documents} kbId={kbId} />
					)}
				</div>
			</main>
		</div>
	);
}

function ScopeBadge({ scope }: { scope: string }) {
	const colors: Record<string, string> = {
		personal: "bg-emerald-500/10 text-emerald-400 ring-emerald-500/20",
		team: "bg-blue-500/10 text-blue-400 ring-blue-500/20",
		department: "bg-purple-500/10 text-purple-400 ring-purple-500/20",
		organization: "bg-amber-500/10 text-amber-400 ring-amber-500/20",
	};

	return (
		<span
			className={cn(
				"rounded-full px-2.5 py-0.5 text-xs font-medium capitalize ring-1",
				colors[scope] || colors.personal,
			)}
		>
			{scope}
		</span>
	);
}

function DocumentUploadZone({ kbId }: { kbId: string }) {
	const [isDragging, setIsDragging] = useState(false);
	const uploadDocument = useUploadDocument();
	const [uploadQueue, setUploadQueue] = useState<
		{ file: File; status: "pending" | "uploading" | "done" | "error" }[]
	>([]);

	const handleFiles = useCallback(
		async (files: FileList | File[]) => {
			const fileArray = Array.from(files);
			const newItems = fileArray.map((file) => ({
				file,
				status: "pending" as const,
			}));
			setUploadQueue((prev) => [...prev, ...newItems]);

			for (let i = 0; i < fileArray.length; i++) {
				const file = fileArray[i];
				setUploadQueue((prev) =>
					prev.map((item) =>
						item.file === file ? { ...item, status: "uploading" } : item,
					),
				);

				try {
					await uploadDocument.mutateAsync({ kbId, file });
					setUploadQueue((prev) =>
						prev.map((item) =>
							item.file === file ? { ...item, status: "done" } : item,
						),
					);
				} catch (_err) {
					setUploadQueue((prev) =>
						prev.map((item) =>
							item.file === file ? { ...item, status: "error" } : item,
						),
					);
				}
			}

			// Clear completed uploads after delay
			setTimeout(() => {
				setUploadQueue((prev) => prev.filter((item) => item.status !== "done"));
			}, 2000);
		},
		[kbId, uploadDocument],
	);

	const handleDrop = useCallback(
		(e: React.DragEvent) => {
			e.preventDefault();
			setIsDragging(false);
			if (e.dataTransfer.files.length) {
				handleFiles(e.dataTransfer.files);
			}
		},
		[handleFiles],
	);

	const handleDragOver = useCallback((e: React.DragEvent) => {
		e.preventDefault();
		setIsDragging(true);
	}, []);

	const handleDragLeave = useCallback((e: React.DragEvent) => {
		e.preventDefault();
		setIsDragging(false);
	}, []);

	return (
		<div>
			{/* Drop Zone */}
			<div
				onDrop={handleDrop}
				onDragOver={handleDragOver}
				onDragLeave={handleDragLeave}
				className={cn(
					"relative rounded-xl border-2 border-dashed transition-all",
					isDragging
						? "border-blue-500 bg-blue-500/5"
						: "border-neutral-800 hover:border-neutral-700",
				)}
			>
				<input
					type="file"
					multiple
					accept=".pdf,.docx,.txt,.md"
					onChange={(e) => e.target.files && handleFiles(e.target.files)}
					className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
				/>
				<div className="flex flex-col items-center justify-center py-10">
					<div
						className={cn(
							"mb-4 flex size-14 items-center justify-center rounded-xl transition-colors",
							isDragging
								? "bg-blue-500/20 text-blue-400"
								: "bg-neutral-800 text-neutral-500",
						)}
					>
						<svg
							className="size-7"
							fill="none"
							viewBox="0 0 24 24"
							stroke="currentColor"
							strokeWidth={1.5}
						>
							<path
								strokeLinecap="round"
								strokeLinejoin="round"
								d="M3 16.5v2.25A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75V16.5m-13.5-9L12 3m0 0 4.5 4.5M12 3v13.5"
							/>
						</svg>
					</div>
					<p className="mb-1 text-sm font-medium text-neutral-300">
						{isDragging ? "Drop files here" : "Drag and drop files here"}
					</p>
					<p className="text-xs text-neutral-500">
						or click to browse • PDF, DOCX, TXT, MD
					</p>
				</div>
			</div>

			{/* Upload Queue */}
			{uploadQueue.length > 0 && (
				<div className="mt-4 space-y-2">
					{uploadQueue.map((item) => (
						<div
							key={item.file.name}
							className="flex items-center gap-3 rounded-lg border border-neutral-800 bg-neutral-900 px-4 py-3"
						>
							<FileIcon mimeType={item.file.type} />
							<div className="flex-1 min-w-0">
								<p className="text-sm font-medium text-neutral-200 truncate">
									{item.file.name}
								</p>
								<p className="text-xs text-neutral-500">
									{formatFileSize(item.file.size)}
								</p>
							</div>
							<div className="flex-shrink-0">
								{item.status === "pending" && (
									<span className="text-xs text-neutral-500">Waiting...</span>
								)}
								{item.status === "uploading" && (
									<div className="size-5 animate-spin rounded-full border-2 border-neutral-600 border-t-blue-500" />
								)}
								{item.status === "done" && (
									<svg
										className="size-5 text-emerald-500"
										fill="none"
										viewBox="0 0 24 24"
										stroke="currentColor"
										strokeWidth={2}
									>
										<path
											strokeLinecap="round"
											strokeLinejoin="round"
											d="m4.5 12.75 6 6 9-13.5"
										/>
									</svg>
								)}
								{item.status === "error" && (
									<svg
										className="size-5 text-red-500"
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
								)}
							</div>
						</div>
					))}
				</div>
			)}
		</div>
	);
}

function DocumentTable({
	documents,
	kbId,
}: {
	documents: Document[];
	kbId: string;
}) {
	const deleteDocument = useDeleteDocument();
	const [deletingId, setDeletingId] = useState<string | null>(null);

	const handleDelete = async (docId: string) => {
		if (deletingId) return;
		setDeletingId(docId);
		try {
			await deleteDocument.mutateAsync({ kbId, docId });
		} catch (err) {
			console.error("Failed to delete:", err);
		} finally {
			setDeletingId(null);
		}
	};

	return (
		<div className="overflow-hidden rounded-xl border border-neutral-800">
			<table className="w-full">
				<thead className="border-b border-neutral-800 bg-neutral-900/50">
					<tr>
						<th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-neutral-500">
							File
						</th>
						<th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-neutral-500">
							Size
						</th>
						<th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-neutral-500">
							Status
						</th>
						<th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-neutral-500">
							Chunks
						</th>
						<th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-neutral-500">
							Uploaded
						</th>
						<th className="px-4 py-3 text-right text-xs font-medium uppercase tracking-wider text-neutral-500">
							Actions
						</th>
					</tr>
				</thead>
				<tbody className="divide-y divide-neutral-800">
					{documents.map((doc) => (
						<tr
							key={doc.id}
							className="group hover:bg-neutral-900/50 transition-colors"
						>
							<td className="px-4 py-3">
								<div className="flex items-center gap-3">
									<FileIcon mimeType={doc.mime_type} />
									<span className="text-sm font-medium text-neutral-200 truncate max-w-[200px]">
										{doc.filename}
									</span>
								</div>
							</td>
							<td className="px-4 py-3 text-sm text-neutral-400">
								{formatFileSize(doc.file_size_bytes)}
							</td>
							<td className="px-4 py-3">
								<StatusBadge status={doc.status} />
							</td>
							<td className="px-4 py-3 text-sm text-neutral-400">
								{doc.chunk_count > 0 ? doc.chunk_count : "—"}
							</td>
							<td className="px-4 py-3 text-sm text-neutral-500">
								{formatDate(doc.created_at)}
							</td>
							<td className="px-4 py-3 text-right">
								<button
									onClick={() => handleDelete(doc.id)}
									disabled={deletingId === doc.id}
									className="rounded-md p-1.5 text-neutral-500 opacity-0 transition-all hover:bg-neutral-800 hover:text-red-400 group-hover:opacity-100 disabled:opacity-50"
								>
									{deletingId === doc.id ? (
										<div className="size-4 animate-spin rounded-full border-2 border-neutral-600 border-t-red-500" />
									) : (
										<svg
											className="size-4"
											fill="none"
											viewBox="0 0 24 24"
											stroke="currentColor"
											strokeWidth={2}
										>
											<path
												strokeLinecap="round"
												strokeLinejoin="round"
												d="m14.74 9-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 0 1-2.244 2.077H8.084a2.25 2.25 0 0 1-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 0 0-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 0 1 3.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 0 0-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 0 0-7.5 0"
											/>
										</svg>
									)}
								</button>
							</td>
						</tr>
					))}
				</tbody>
			</table>
		</div>
	);
}

function FileIcon({ mimeType }: { mimeType: string }) {
	const getColor = () => {
		if (mimeType.includes("pdf")) return "text-red-400 bg-red-500/10";
		if (mimeType.includes("word") || mimeType.includes("docx"))
			return "text-blue-400 bg-blue-500/10";
		if (mimeType.includes("text") || mimeType.includes("markdown"))
			return "text-neutral-400 bg-neutral-500/10";
		return "text-neutral-400 bg-neutral-500/10";
	};

	return (
		<div
			className={cn(
				"flex size-9 items-center justify-center rounded-lg",
				getColor(),
			)}
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
					d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z"
				/>
			</svg>
		</div>
	);
}

function StatusBadge({ status }: { status: string }) {
	const styles: Record<string, string> = {
		pending: "bg-neutral-500/10 text-neutral-400 ring-neutral-500/20",
		processing: "bg-amber-500/10 text-amber-400 ring-amber-500/20",
		completed: "bg-emerald-500/10 text-emerald-400 ring-emerald-500/20",
		failed: "bg-red-500/10 text-red-400 ring-red-500/20",
	};

	return (
		<span
			className={cn(
				"inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-xs font-medium capitalize ring-1",
				styles[status] || styles.pending,
			)}
		>
			{status === "processing" && (
				<div className="size-2 animate-pulse rounded-full bg-amber-400" />
			)}
			{status}
		</span>
	);
}

function formatFileSize(bytes: number): string {
	if (bytes < 1024) return `${bytes} B`;
	if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
	return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function formatDate(dateString: string): string {
	const date = new Date(dateString);
	if (Number.isNaN(date.getTime())) return "Unknown";
	return date.toLocaleDateString(undefined, {
		month: "short",
		day: "numeric",
		hour: "2-digit",
		minute: "2-digit",
	});
}
