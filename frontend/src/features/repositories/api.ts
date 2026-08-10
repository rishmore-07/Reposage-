import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import apiClient from "@/lib/api-client";
import { QUERY_KEYS } from "@/constants/query-keys";

export interface Repository {
  id: string;
  full_name: string;
  name: string;
  description: string | null;
  html_url: string;
  status: string;
  is_private: boolean;
  default_branch: string;
  analysis_error?: string | null;
  created_at: string;
}

export interface RepositoryIngestion {
  id: string;
  repository_id: string;
  status: "pending" | "running" | "completed" | "failed";
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
  error_message: string | null;
  progress_message: string | null;
  
  // Metrics
  file_count: number;
  parsed_file_count: number;
  symbol_count: number;
  unsupported_file_count: number;
  parse_error_count: number;
}

export interface GitHubRepository {
  id: number;
  full_name: string;
  name: string;
  description: string | null;
  html_url: string;
  private: boolean;
}

export interface GitHubRepositoryListResponse {
  total_count?: number | null;
  has_next: boolean;
  items: GitHubRepository[];
  page: number;
  per_page: number;
}

export const useAvailableRepositories = (q?: string, page: number = 1) => {
  return useQuery({
    queryKey: ["repositories", "available", q, page],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (q) params.append("q", q);
      params.append("page", page.toString());
      
      const { data } = await apiClient.get<GitHubRepositoryListResponse>(
        `/api/v1/repositories/available?${params.toString()}`
      );
      return data;
    },
  });
};

export const useConnectRepository = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (github_repo_id: number) => {
      const { data } = await apiClient.post<Repository>("/api/v1/repositories", {
        github_repo_id,
        organization_id: null,
      });
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.repositories.list() });
    },
  });
};

export const useDisconnectRepository = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (repository_id: string) => {
      await apiClient.delete(`/api/v1/repositories/${repository_id}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.repositories.list() });
    },
  });
};

export const useRepository = (id: string) => {
  return useQuery({
    queryKey: ["repositories", "detail", id],
    queryFn: async () => {
      const { data } = await apiClient.get<Repository>(`/api/v1/repositories/${id}`);
      return data;
    },
    enabled: !!id,
  });
};

export const useStartIngestion = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (repository_id: string) => {
      const { data } = await apiClient.post<RepositoryIngestion>(`/api/v1/repositories/${repository_id}/ingest`);
      return data;
    },
    onSuccess: (_, repository_id) => {
      queryClient.invalidateQueries({ queryKey: ["repositories", "ingestion", repository_id] });
    },
  });
};

export const useIngestionStatus = (repository_id: string) => {
  return useQuery({
    queryKey: ["repositories", "ingestion", repository_id],
    queryFn: async () => {
      const { data } = await apiClient.get<RepositoryIngestion>(`/api/v1/repositories/${repository_id}/ingestion`);
      return data;
    },
    enabled: !!repository_id,
    retry: false, // Don't retry automatically if 404
    refetchInterval: (query) => {
      // Poll every 3 seconds if status is pending or running
      const state = query.state.data;
      if (state && (state.status === "pending" || state.status === "running")) {
        return 3000;
      }
      return false;
    },
  });
};
