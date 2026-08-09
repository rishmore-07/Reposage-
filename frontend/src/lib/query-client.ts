/**
 * src/lib/query-client.ts
 *
 * TanStack Query (React Query) client configuration.
 *
 * Key decisions:
 * - staleTime: 30 seconds — data is considered fresh and won't refetch
 * - retry: 1 — retry failed requests once before showing error UI
 * - refetchOnWindowFocus: true — refresh stale data when user returns to tab
 * - No global onError handler — errors are handled at the component level
 *   via TanStack Query's error state (better UX, more granular control)
 */
import { QueryClient } from "@tanstack/react-query";

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      // Data is considered fresh for 30 seconds
      staleTime: 30 * 1000,
      // Keep unused data in cache for 5 minutes
      gcTime: 5 * 60 * 1000,
      // Retry once on failure (for transient network errors)
      retry: 1,
      // Retry after 1 second
      retryDelay: 1000,
      // Refetch when user returns to the tab (catches updates made elsewhere)
      refetchOnWindowFocus: true,
      // Don't refetch on reconnect by default (avoid hammering API on spotty connections)
      refetchOnReconnect: false,
    },
    mutations: {
      // Don't retry failed mutations (side effects are not idempotent)
      retry: false,
    },
  },
});
