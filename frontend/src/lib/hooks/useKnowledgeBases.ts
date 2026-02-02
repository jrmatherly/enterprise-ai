"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/lib/api/client";

export interface KnowledgeBase {
  id: string;
  name: string;
  description: string | null;
  scope: "personal" | "team" | "department" | "organization";
  document_count: number;
  is_shared: boolean;
  created_at: string;
  updated_at: string;
}

export interface Document {
  id: string;
  filename: string;
  mime_type: string;
  file_size_bytes: number;
  status: "pending" | "processing" | "completed" | "failed";
  chunk_count: number;
  created_at: string;
  processed_at: string | null;
}

export interface CreateKBRequest {
  name: string;
  description?: string;
  scope?: "personal" | "team" | "department" | "organization";
}

/**
 * Fetch all knowledge bases
 */
export function useKnowledgeBases() {
  return useQuery({
    queryKey: ["knowledge-bases"],
    queryFn: async () => {
      return apiClient<KnowledgeBase[]>("/api/v1/knowledge-bases");
    },
    staleTime: 30 * 1000,
  });
}

/**
 * Fetch a single knowledge base
 */
export function useKnowledgeBase(kbId: string | null) {
  return useQuery({
    queryKey: ["knowledge-base", kbId],
    queryFn: async () => {
      if (!kbId) return null;
      return apiClient<KnowledgeBase>(`/api/v1/knowledge-bases/${kbId}`);
    },
    enabled: !!kbId,
    staleTime: 30 * 1000,
  });
}

/**
 * Create a new knowledge base
 */
export function useCreateKnowledgeBase() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: CreateKBRequest) => {
      return apiClient<KnowledgeBase>("/api/v1/knowledge-bases", {
        method: "POST",
        body: JSON.stringify(data),
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["knowledge-bases"] });
    },
  });
}

/**
 * Fetch documents in a knowledge base
 */
export function useDocuments(kbId: string | null) {
  return useQuery({
    queryKey: ["documents", kbId],
    queryFn: async () => {
      if (!kbId) return [];
      return apiClient<Document[]>(`/api/v1/knowledge-bases/${kbId}/documents`);
    },
    enabled: !!kbId,
    staleTime: 10 * 1000,
  });
}

/**
 * Upload a document to a knowledge base
 */
export function useUploadDocument() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ kbId, file }: { kbId: string; file: File }) => {
      const formData = new FormData();
      formData.append("file", file);

      const response = await fetch(
        `/api/v1/knowledge-bases/${kbId}/documents`,
        {
          method: "POST",
          credentials: "include",
          body: formData,
        },
      );

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || "Upload failed");
      }

      return response.json() as Promise<Document>;
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({
        queryKey: ["documents", variables.kbId],
      });
      queryClient.invalidateQueries({ queryKey: ["knowledge-bases"] });
    },
  });
}

/**
 * Delete a document
 */
export function useDeleteDocument() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ kbId, docId }: { kbId: string; docId: string }) => {
      return apiClient<void>(
        `/api/v1/knowledge-bases/${kbId}/documents/${docId}`,
        {
          method: "DELETE",
        },
      );
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({
        queryKey: ["documents", variables.kbId],
      });
      queryClient.invalidateQueries({ queryKey: ["knowledge-bases"] });
    },
  });
}

/**
 * Delete a knowledge base
 */
export function useDeleteKnowledgeBase() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (kbId: string) => {
      return apiClient<void>(`/api/v1/knowledge-bases/${kbId}`, {
        method: "DELETE",
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["knowledge-bases"] });
    },
  });
}
