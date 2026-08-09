/**
 * src/pages/RepositoriesPage.tsx
 *
 * Repositories list page.
 * Fetches and displays the user's connected GitHub repositories.
 */
import { BookOpen, Plus } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import apiClient from "@/lib/api-client";
import { QUERY_KEYS } from "@/constants/query-keys";
import { LoadingSpinner } from "@/components/feedback/LoadingSpinner";
import type { Page } from "@/types/api";

interface Repository {
  id: string;
  full_name: string;
  name: string;
  description: string | null;
  html_url: string;
  status: string;
  is_private: boolean;
  created_at: string;
}

const STATUS_COLORS: Record<string, string> = {
  ready: "text-emerald-500 bg-emerald-500/10",
  pending: "text-yellow-500 bg-yellow-500/10",
  queued: "text-blue-500 bg-blue-500/10",
  cloning: "text-blue-500 bg-blue-500/10",
  analyzing: "text-primary bg-primary/10",
  failed: "text-destructive bg-destructive/10",
  stale: "text-orange-500 bg-orange-500/10",
};

export function RepositoriesPage() {
  const { data, isLoading, isError } = useQuery({
    queryKey: QUERY_KEYS.repositories.list(),
    queryFn: async () => {
      const { data } = await apiClient.get<Page<Repository>>(
        "/api/v1/repositories"
      );
      return data;
    },
  });

  return (
    <div className="animate-page-enter p-6 lg:p-8">
      {/* ── Page header ──────────────────────────────────────────────────── */}
      <div className="mb-6 flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2 text-sm font-medium text-muted-foreground">
            <BookOpen className="h-4 w-4" />
            <span>Repositories</span>
          </div>
          <h1 className="mt-1 text-2xl font-bold text-foreground">
            Your Repositories
          </h1>
          <p className="mt-1 text-muted-foreground">
            Connect and analyze your GitHub repositories.
          </p>
        </div>

        <button
          id="connect-repo-button"
          className="flex items-center gap-2 rounded-lg bg-primary px-4 py-2.5 text-sm font-semibold text-primary-foreground shadow-md shadow-primary/25 transition-all hover:bg-primary/90"
        >
          <Plus className="h-4 w-4" />
          Connect repository
        </button>
      </div>

      {/* ── Content ──────────────────────────────────────────────────────── */}
      {isLoading && (
        <LoadingSpinner fullPage label="Loading repositories..." />
      )}

      {isError && (
        <div className="glass-card rounded-xl p-6 text-center text-destructive">
          Failed to load repositories. Please try again.
        </div>
      )}

      {!isLoading && !isError && data && data.items.length === 0 && (
        /* Empty state */
        <div className="glass-card flex flex-col items-center justify-center rounded-xl p-16 text-center">
          <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-primary/10">
            <BookOpen className="h-8 w-8 text-primary" />
          </div>
          <h2 className="text-lg font-semibold text-foreground">
            No repositories yet
          </h2>
          <p className="mt-2 max-w-sm text-sm text-muted-foreground">
            Connect your GitHub repositories to start running AI-powered
            analysis and generating insights.
          </p>
          <button
            id="connect-first-repo-button"
            className="mt-6 flex items-center gap-2 rounded-lg bg-primary px-5 py-2.5 text-sm font-semibold text-primary-foreground shadow-md shadow-primary/25 hover:bg-primary/90 transition-all"
          >
            <Plus className="h-4 w-4" />
            Connect your first repository
          </button>
        </div>
      )}

      {!isLoading && !isError && data && data.items.length > 0 && (
        <div className="space-y-3">
          {data.items.map((repo) => (
            <div
              key={repo.id}
              className="glass-card flex items-center justify-between rounded-xl p-5 transition-all hover:border-border/80 hover:shadow-sm"
            >
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <BookOpen className="h-4 w-4 shrink-0 text-muted-foreground" />
                  <span className="truncate font-medium text-foreground">
                    {repo.full_name}
                  </span>
                  {repo.is_private && (
                    <span className="rounded-full bg-muted px-2 py-0.5 text-xs text-muted-foreground">
                      Private
                    </span>
                  )}
                </div>
                {repo.description && (
                  <p className="mt-1 truncate text-sm text-muted-foreground">
                    {repo.description}
                  </p>
                )}
              </div>
              <div className="ml-4 shrink-0">
                <span
                  className={`rounded-full px-3 py-1 text-xs font-medium capitalize ${
                    STATUS_COLORS[repo.status] ?? "text-muted-foreground bg-muted"
                  }`}
                >
                  {repo.status}
                </span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
