import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";
import { useAvailableRepositories, useConnectRepository, useDisconnectRepository, useRepository } from "./api";
import apiClient from "@/lib/api-client";

// Mock the API client
vi.mock("@/lib/api-client", () => {
  return {
    default: {
      get: vi.fn(),
      post: vi.fn(),
      delete: vi.fn(),
    },
  };
});

// Setup React Query wrapper
const createTestQueryClient = () => new QueryClient({
  defaultOptions: {
    queries: {
      retry: false,
    },
  },
});

export function createWrapper() {
  const testQueryClient = createTestQueryClient();
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={testQueryClient}>{children}</QueryClientProvider>
  );
}

describe("Repository API Hooks", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("useAvailableRepositories", () => {
    it("fetches available repositories", async () => {
      const mockData = { items: [{ id: 1, name: "test-repo" }], total_count: 1, page: 1, per_page: 20 };
      vi.mocked(apiClient.get).mockResolvedValueOnce({ data: mockData });

      const { result } = renderHook(() => useAvailableRepositories("test"), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      
      expect(result.current.data).toEqual(mockData);
      expect(apiClient.get).toHaveBeenCalledWith("/api/v1/repositories/available?q=test&page=1");
    });
  });

  describe("useConnectRepository", () => {
    it("posts connection request", async () => {
      const mockRepo = { id: "uuid", name: "test-repo" };
      vi.mocked(apiClient.post).mockResolvedValueOnce({ data: mockRepo });

      const { result } = renderHook(() => useConnectRepository(), {
        wrapper: createWrapper(),
      });

      result.current.mutate(123);

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      
      expect(result.current.data).toEqual(mockRepo);
      expect(apiClient.post).toHaveBeenCalledWith("/api/v1/repositories", {
        github_repo_id: 123,
        organization_id: null,
      });
    });
  });

  describe("useDisconnectRepository", () => {
    it("deletes connection", async () => {
      vi.mocked(apiClient.delete).mockResolvedValueOnce({ data: null });

      const { result } = renderHook(() => useDisconnectRepository(), {
        wrapper: createWrapper(),
      });

      result.current.mutate("repo-uuid");

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      
      expect(apiClient.delete).toHaveBeenCalledWith("/api/v1/repositories/repo-uuid");
    });
  });

  describe("useRepository", () => {
    it("fetches repository details", async () => {
      const mockRepo = { id: "repo-uuid", name: "test-repo" };
      vi.mocked(apiClient.get).mockResolvedValueOnce({ data: mockRepo });

      const { result } = renderHook(() => useRepository("repo-uuid"), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      
      expect(result.current.data).toEqual(mockRepo);
      expect(apiClient.get).toHaveBeenCalledWith("/api/v1/repositories/repo-uuid");
    });
  });
});
