import { useParams, Link, useNavigate } from "react-router-dom";
import { ArrowLeft, Github, Trash2, Shield, Calendar, GitBranch, AlertTriangle } from "lucide-react";
import { useRepository, useDisconnectRepository } from "@/features/repositories/api";
import { LoadingSpinner } from "@/components/feedback/LoadingSpinner";
import { ROUTES } from "@/constants/routes";

export function RepositoryDetailPage() {
  const { repositoryId } = useParams<{ repositoryId: string }>();
  const navigate = useNavigate();

  const { data: repo, isLoading, isError } = useRepository(repositoryId || "");
  const disconnectMutation = useDisconnectRepository();

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
        </div>

        {/* Right Column - Status */}
        <div className="space-y-6">
          <div className="glass-card p-6 rounded-xl">
            <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
              Analysis Status
            </h2>
            
            <div className="space-y-4">
              <div>
                <p className="text-sm text-muted-foreground mb-1">Current State</p>
                <div className="inline-flex items-center rounded-full bg-muted px-3 py-1 text-sm font-medium capitalize">
                  {repo.status}
                </div>
              </div>

              {repo.status === "pending" && (
                <div className="rounded-lg bg-blue-500/10 p-3 text-sm text-blue-500 border border-blue-500/20">
                  <p>Repository is connected. Analysis is not yet available in Phase 2.</p>
                </div>
              )}

              {repo.status === "failed" && repo.analysis_error && (
                <div className="rounded-lg bg-destructive/10 p-3 text-sm text-destructive border border-destructive/20 flex gap-2">
                  <AlertTriangle className="h-4 w-4 shrink-0 mt-0.5" />
                  <p>{repo.analysis_error}</p>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
