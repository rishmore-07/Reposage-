import { useState } from "react";
import { Search, Github, ArrowLeft, Check, Plus } from "lucide-react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { useAvailableRepositories, useConnectRepository } from "@/features/repositories/api";
import { LoadingSpinner } from "@/components/feedback/LoadingSpinner";
import { QUERY_KEYS } from "@/constants/query-keys";
import apiClient from "@/lib/api-client";
import type { Page } from "@/types/api";

export function ConnectRepositoryPage() {
  const [searchQuery, setSearchQuery] = useState("");
  const [page, setPage] = useState(1);

  // Debounced search could be added here, but for simplicity we'll just trigger on button or enter
  const [activeQuery, setActiveQuery] = useState("");

  const { data: availableData, isLoading, isError } = useAvailableRepositories(activeQuery, page);
  const connectMutation = useConnectRepository();

  // Fetch already connected repos to show "Connected" state
  const { data: connectedData } = useQuery({
    queryKey: QUERY_KEYS.repositories.list(),
    queryFn: async () => {
      const { data } = await apiClient.get<Page<{ github_repo_id: number }>>("/api/v1/repositories");
      return data;
    },
  });

  const connectedIds = new Set(connectedData?.items.map((r) => r.github_repo_id) || []);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setActiveQuery(searchQuery);
    setPage(1);
  };

  return (
    <div className="animate-page-enter p-6 lg:p-8 max-w-5xl mx-auto">
      <div className="mb-6 flex items-center gap-4">
        <Link
          to="/repositories"
          className="flex h-10 w-10 items-center justify-center rounded-full hover:bg-muted transition-colors"
        >
          <ArrowLeft className="h-5 w-5 text-muted-foreground" />
        </Link>
        <div>
          <h1 className="text-2xl font-bold text-foreground flex items-center gap-2">
            <Github className="h-6 w-6" />
            Connect GitHub Repository
          </h1>
          <p className="mt-1 text-muted-foreground">
            Search and connect repositories from your GitHub account.
          </p>
        </div>
      </div>

      <div className="glass-card p-4 rounded-xl mb-6">
        <form onSubmit={handleSearch} className="flex gap-2">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-muted-foreground" />
            <input
              type="text"
              placeholder="Search repositories..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full rounded-lg bg-background border border-border/50 py-2.5 pl-10 pr-4 text-sm outline-none focus:border-primary/50 focus:ring-1 focus:ring-primary/50 transition-all"
            />
          </div>
          <button
            type="submit"
            className="rounded-lg bg-primary px-6 py-2.5 text-sm font-semibold text-primary-foreground shadow-md shadow-primary/25 hover:bg-primary/90 transition-all"
          >
            Search
          </button>
        </form>
      </div>

      {isLoading && (
        <div className="py-12">
          <LoadingSpinner label="Fetching repositories from GitHub..." />
        </div>
      )}

      {isError && (
        <div className="glass-card rounded-xl p-6 text-center text-destructive">
          Failed to fetch repositories from GitHub. Are you logged in via GitHub?
        </div>
      )}

      {!isLoading && !isError && availableData && (
        <div className="space-y-4">
          <p className="text-sm text-muted-foreground mb-2">
            Showing {availableData.items.length} repositories
            {availableData.total_count != null ? ` of ${availableData.total_count}` : ""}
          </p>
          
          <div className="grid gap-3 sm:grid-cols-2">
            {availableData.items.map((repo) => {
              const isConnected = connectedIds.has(repo.id);
              const isConnecting = connectMutation.isPending && connectMutation.variables === repo.id;

              return (
                <div
                  key={repo.id}
                  className="glass-card flex flex-col justify-between rounded-xl p-5 transition-all hover:border-border/80 hover:shadow-sm"
                >
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      <Github className="h-4 w-4 shrink-0 text-muted-foreground" />
                      <span className="truncate font-semibold text-foreground">
                        {repo.full_name}
                      </span>
                      {repo.private && (
                        <span className="rounded-full bg-muted px-2 py-0.5 text-xs text-muted-foreground">
                          Private
                        </span>
                      )}
                    </div>
                    {repo.description && (
                      <p className="truncate text-sm text-muted-foreground mb-4">
                        {repo.description}
                      </p>
                    )}
                  </div>
                  
                  <div className="flex justify-end mt-4">
                    {isConnected ? (
                      <button
                        disabled
                        className="flex items-center gap-1.5 rounded-lg bg-emerald-500/10 px-3 py-1.5 text-sm font-medium text-emerald-500"
                      >
                        <Check className="h-4 w-4" />
                        Connected
                      </button>
                    ) : (
                      <button
                        onClick={() => connectMutation.mutate(repo.id)}
                        disabled={isConnecting}
                        className="flex items-center gap-1.5 rounded-lg bg-primary/10 px-3 py-1.5 text-sm font-medium text-primary hover:bg-primary/20 transition-colors disabled:opacity-50"
                      >
                        {isConnecting ? (
                          <LoadingSpinner size="sm" />
                        ) : (
                          <Plus className="h-4 w-4" />
                        )}
                        {isConnecting ? "Connecting..." : "Connect"}
                      </button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>

          {availableData.items.length === 0 && (
            <div className="text-center py-12 text-muted-foreground">
              No repositories found matching your search.
            </div>
          )}

          <div className="flex justify-center gap-2 mt-6 pt-4">
            <button
              disabled={page === 1}
              onClick={() => setPage(p => p - 1)}
              className="px-4 py-2 text-sm rounded-lg border border-border/50 disabled:opacity-50 hover:bg-muted"
            >
              Previous
            </button>
            <span className="px-4 py-2 text-sm">Page {page}</span>
            <button
              disabled={!availableData.has_next}
              onClick={() => setPage(p => p + 1)}
              className="px-4 py-2 text-sm rounded-lg border border-border/50 disabled:opacity-50 hover:bg-muted"
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
