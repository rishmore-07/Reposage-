import { useParams, Link, useNavigate } from "react-router-dom";
import { useState } from "react";
import { ArrowLeft, Github, Trash2, Shield, Calendar, GitBranch, AlertTriangle, PlayCircle, Loader2, CheckCircle, XCircle, Search } from "lucide-react";
import { useRepository, useDisconnectRepository, useStartIngestion, useIngestionStatus, useSemanticSearch } from "@/features/repositories/api";
import { LoadingSpinner } from "@/components/feedback/LoadingSpinner";
import { ROUTES } from "@/constants/routes";

export function RepositoryDetailPage() {
  const { repositoryId } = useParams<{ repositoryId: string }>();
  const navigate = useNavigate();

  const { data: repo, isLoading, isError } = useRepository(repositoryId || "");
  const disconnectMutation = useDisconnectRepository();
  const startIngestionMutation = useStartIngestion();
  const { data: ingestion } = useIngestionStatus(repositoryId || "");
  const searchMutation = useSemanticSearch();
  const [searchQuery, setSearchQuery] = useState("");

  if (isLoading) {
    return <LoadingSpinner fullPage label="Loading repository details..." />;
  }

  if (isError || !repo) {
    return (
      <div className="p-8 text-center text-destructive">
        Failed to load repository details. It may have been disconnected or you don't have access.
      </div>
    );
  }

  const handleDisconnect = async () => {
    if (confirm("Are you sure you want to disconnect this repository?")) {
      await disconnectMutation.mutateAsync(repo.id);
      navigate(ROUTES.REPOSITORIES);
    }
  };

  const handleStartAnalysis = async () => {
    await startIngestionMutation.mutateAsync(repo.id);
  };

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!searchQuery.trim()) return;
    await searchMutation.mutateAsync({ repository_id: repo.id, query: searchQuery });
  };

  return (
    <div className="animate-page-enter p-6 lg:p-8 max-w-5xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Link
            to={ROUTES.REPOSITORIES}
            className="flex h-10 w-10 items-center justify-center rounded-full hover:bg-muted transition-colors"
          >
            <ArrowLeft className="h-5 w-5 text-muted-foreground" />
          </Link>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-2xl font-bold text-foreground">{repo.name}</h1>
              {repo.is_private && (
                <span className="rounded-full bg-muted px-2.5 py-0.5 text-xs font-medium text-muted-foreground border border-border/50">
                  <Shield className="inline h-3 w-3 mr-1" />
                  Private
                </span>
              )}
            </div>
            <p className="mt-1 text-muted-foreground flex items-center gap-2">
              <Github className="h-4 w-4" />
              {repo.full_name}
            </p>
          </div>
        </div>

        <button
          onClick={handleDisconnect}
          disabled={disconnectMutation.isPending}
          className="flex items-center gap-2 rounded-lg border border-destructive/20 bg-destructive/10 px-4 py-2 text-sm font-semibold text-destructive hover:bg-destructive hover:text-destructive-foreground transition-all disabled:opacity-50"
        >
          {disconnectMutation.isPending ? (
            <LoadingSpinner size="sm" />
          ) : (
            <Trash2 className="h-4 w-4" />
          )}
          Disconnect
        </button>
      </div>

      {/* Main Content Grid */}
      <div className="grid gap-6 md:grid-cols-3">
        {/* Left Column - Details */}
        <div className="md:col-span-2 space-y-6">
          <div className="glass-card p-6 rounded-xl">
            <h2 className="text-lg font-semibold mb-4">About</h2>
            {repo.description ? (
              <p className="text-foreground">{repo.description}</p>
            ) : (
              <p className="text-muted-foreground italic">No description provided.</p>
            )}
            
            <div className="mt-6 flex flex-wrap gap-4 text-sm text-muted-foreground">
              <div className="flex items-center gap-1.5 bg-muted/50 px-3 py-1.5 rounded-md">
                <GitBranch className="h-4 w-4" />
                Default branch: <span className="font-medium text-foreground">{repo.default_branch}</span>
              </div>
              <div className="flex items-center gap-1.5 bg-muted/50 px-3 py-1.5 rounded-md">
                <Calendar className="h-4 w-4" />
                Connected: <span className="font-medium text-foreground">{new Date(repo.created_at).toLocaleDateString()}</span>
              </div>
            </div>
          </div>

          {/* Semantic Search Section */}
          {ingestion?.status === "completed" && (
            <div className="glass-card p-6 rounded-xl">
              <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
                <Search className="h-5 w-5 text-primary" />
                Semantic Code Search
              </h2>
              <form onSubmit={handleSearch} className="flex gap-3 mb-6">
                <input
                  type="text"
                  placeholder="e.g., 'What handles GitHub OAuth?'"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="flex-1 rounded-lg border border-border/50 bg-background/50 px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
                  disabled={searchMutation.isPending}
                />
                <button
                  type="submit"
                  disabled={searchMutation.isPending || !searchQuery.trim()}
                  className="rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground hover:bg-primary/90 disabled:opacity-50 flex items-center gap-2"
                >
                  {searchMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : "Search"}
                </button>
              </form>

              {searchMutation.data?.results && (
                <div className="space-y-4">
                  {searchMutation.data.results.length === 0 ? (
                    <p className="text-muted-foreground text-sm">No results found.</p>
                  ) : (
                    searchMutation.data.results.map((result) => (
                      <div key={result.chunk_id} className="border border-border/50 rounded-lg p-4 bg-muted/20">
                        <div className="flex justify-between items-start mb-2">
                          <div>
                            <p className="text-sm font-medium text-foreground">{result.file_path}</p>
                            {result.symbol_name && (
                              <p className="text-xs text-muted-foreground">{result.chunk_type}: {result.symbol_name}</p>
                            )}
                          </div>
                          <span className="text-xs font-medium bg-primary/10 text-primary px-2 py-1 rounded-full">
                            Score: {result.score.toFixed(2)}
                          </span>
                        </div>
                        <pre className="mt-3 p-3 bg-background/50 rounded text-xs overflow-x-auto border border-border/30">
                          <code>{result.content}</code>
                        </pre>
                        <p className="mt-2 text-xs text-muted-foreground">
                          Language: {result.language} • Lines: {result.start_line}-{result.end_line}
                        </p>
                      </div>
                    ))
                  )}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Right Column - Status */}
        <div className="space-y-6">
          <div className="glass-card p-6 rounded-xl">
            <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
              Analysis Status
            </h2>
            
            <div className="space-y-4">
              <div>
                <p className="text-sm text-muted-foreground mb-1">Ingestion Status</p>
                <div className="flex items-center gap-2">
                  {ingestion ? (
                    <div className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-sm font-medium capitalize
                      ${ingestion.status === "completed" ? "bg-green-500/10 text-green-500 border border-green-500/20" : ""}
                      ${ingestion.status === "failed" ? "bg-destructive/10 text-destructive border border-destructive/20" : ""}
                      ${(ingestion.status === "pending" || ingestion.status === "running") ? "bg-blue-500/10 text-blue-500 border border-blue-500/20" : ""}
                    `}>
                      {(ingestion.status === "pending" || ingestion.status === "running") && <Loader2 className="h-4 w-4 animate-spin" />}
                      {ingestion.status === "completed" && <CheckCircle className="h-4 w-4" />}
                      {ingestion.status === "failed" && <XCircle className="h-4 w-4" />}
                      {ingestion.status}
                    </div>
                  ) : (
                    <div className="inline-flex items-center rounded-full bg-muted px-3 py-1 text-sm font-medium text-muted-foreground">
                      Not Started
                    </div>
                  )}
                </div>
                
                {ingestion?.progress_message && (
                  <p className="text-xs text-muted-foreground mt-2 animate-pulse">
                    Current step: {ingestion.progress_message}
                  </p>
                )}
                
                {ingestion?.status === "completed" && (
                  <div className="mt-6 space-y-2 border-t border-border/50 pt-4 text-sm">
                    <h3 className="font-medium text-foreground mb-3">Analysis Statistics</h3>
                    <div className="flex justify-between text-muted-foreground">
                      <span>Files discovered:</span>
                      <span className="font-medium text-foreground">{ingestion.file_count}</span>
                    </div>
                    <div className="flex justify-between text-muted-foreground">
                      <span>Files parsed:</span>
                      <span className="font-medium text-foreground">{ingestion.parsed_file_count}</span>
                    </div>
                    <div className="flex justify-between text-muted-foreground">
                      <span>Symbols extracted:</span>
                      <span className="font-medium text-foreground">{ingestion.symbol_count}</span>
                    </div>
                    <div className="flex justify-between text-muted-foreground">
                      <span>Unsupported files:</span>
                      <span className="font-medium text-foreground">{ingestion.unsupported_file_count}</span>
                    </div>
                    <div className="flex justify-between text-muted-foreground">
                      <span>Parse errors:</span>
                      <span className="font-medium text-foreground">{ingestion.parse_error_count}</span>
                    </div>
                  </div>
                )}
              </div>

              {!ingestion || (ingestion.status !== "pending" && ingestion.status !== "running") ? (
                <button
                  onClick={handleStartAnalysis}
                  disabled={startIngestionMutation.isPending}
                  className="w-full flex items-center justify-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground hover:bg-primary/90 transition-all disabled:opacity-50"
                >
                  {startIngestionMutation.isPending ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <PlayCircle className="h-4 w-4" />
                  )}
                  Start Analysis
                </button>
              ) : null}

              {ingestion?.status === "failed" && ingestion.error_message && (
                <div className="rounded-lg bg-destructive/10 p-3 text-sm text-destructive border border-destructive/20 flex gap-2">
                  <AlertTriangle className="h-4 w-4 shrink-0 mt-0.5" />
                  <p>{ingestion.error_message}</p>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
