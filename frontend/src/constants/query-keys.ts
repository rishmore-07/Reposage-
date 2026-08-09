/**
 * src/constants/query-keys.ts
 *
 * TanStack Query key factories.
 *
 * Why key factories?
 * Query keys must be consistent to benefit from caching.
 * String keys scattered across the codebase are error-prone.
 * Factory functions ensure keys are always correctly structured.
 *
 * Usage:
 *   useQuery({ queryKey: QUERY_KEYS.repositories.list() })
 *   queryClient.invalidateQueries({ queryKey: QUERY_KEYS.repositories.all })
 */
export const QUERY_KEYS = {
  // Current user
  currentUser: ["current-user"] as const,

  // Health
  health: ["health"] as const,

  // Repositories
  repositories: {
    all: ["repositories"] as const,
    list: (params?: Record<string, unknown>) =>
      ["repositories", "list", params] as const,
    detail: (id: string) => ["repositories", "detail", id] as const,
  },

  // Organizations
  organizations: {
    all: ["organizations"] as const,
    list: (params?: Record<string, unknown>) =>
      ["organizations", "list", params] as const,
    detail: (id: string) => ["organizations", "detail", id] as const,
    members: (id: string) => ["organizations", id, "members"] as const,
  },

  // API Keys
  apiKeys: {
    all: ["api-keys"] as const,
    list: () => ["api-keys", "list"] as const,
  },

  // Notifications
  notifications: {
    all: ["notifications"] as const,
    list: (params?: Record<string, unknown>) =>
      ["notifications", "list", params] as const,
    unreadCount: () => ["notifications", "unread-count"] as const,
  },
} as const;
