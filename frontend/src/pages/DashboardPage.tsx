/**
 * src/pages/DashboardPage.tsx
 *
 * Main dashboard page — the first page users see after login.
 *
 * Architecture: This page composes feature components.
 * No business logic lives here — it's a pure page composition.
 *
 * Current state: Welcome scaffold ready for metric widgets.
 */
import {
  Activity,
  BookOpen,
  GitBranch,
  Sparkles,
  TrendingUp,
  Zap,
  type LucideIcon,
} from "lucide-react";
import { useAuthStore } from "@/lib/auth-store";

interface StatCardProps {
  title: string;
  value: string;
  change?: string;
  icon: LucideIcon;
  trend?: "up" | "down" | "neutral";
}

function StatCard({ title, value, change, icon: Icon, trend }: StatCardProps) {
  return (
    <div className="glass-card rounded-xl p-5 transition-all duration-200 hover:border-border hover:shadow-md">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm font-medium text-muted-foreground">{title}</p>
          <p className="mt-2 text-3xl font-bold text-foreground">{value}</p>
          {change && (
            <p
              className={`mt-1 text-xs font-medium ${
                trend === "up"
                  ? "text-emerald-500"
                  : trend === "down"
                    ? "text-destructive"
                    : "text-muted-foreground"
              }`}
            >
              {change}
            </p>
          )}
        </div>
        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
          <Icon className="h-5 w-5 text-primary" />
        </div>
      </div>
    </div>
  );
}

export function DashboardPage() {
  const user = useAuthStore((state) => state.user);
  const displayName = user?.full_name ?? user?.email ?? "there";

  return (
    <div className="animate-page-enter p-6 lg:p-8">
      {/* ── Page header ──────────────────────────────────────────────────── */}
      <div className="mb-8">
        <div className="flex items-center gap-2 text-sm font-medium text-muted-foreground">
          <Activity className="h-4 w-4" />
          <span>Overview</span>
        </div>
        <h1 className="mt-2 text-2xl font-bold text-foreground">
          Welcome back,{" "}
          <span className="gradient-text">{displayName}</span> 👋
        </h1>
        <p className="mt-1 text-muted-foreground">
          Here's what's happening with your repositories today.
        </p>
      </div>

      {/* ── Stats grid ───────────────────────────────────────────────────── */}
      <div className="mb-8 grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard
          title="Connected Repos"
          value="0"
          change="Connect your first repository"
          icon={BookOpen}
          trend="neutral"
        />
        <StatCard
          title="Analyses Run"
          value="0"
          change="No analyses yet"
          icon={Zap}
          trend="neutral"
        />
        <StatCard
          title="Insights Generated"
          value="0"
          change="Start by connecting a repo"
          icon={Sparkles}
          trend="neutral"
        />
        <StatCard
          title="Active Branches"
          value="0"
          change="Monitored branches"
          icon={GitBranch}
          trend="neutral"
        />
      </div>

      {/* ── Getting started section ───────────────────────────────────────── */}
      <div className="glass-card rounded-xl p-6">
        <div className="flex items-center gap-3 mb-4">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary/10">
            <TrendingUp className="h-4 w-4 text-primary" />
          </div>
          <div>
            <h2 className="text-base font-semibold text-foreground">
              Getting started
            </h2>
            <p className="text-sm text-muted-foreground">
              Complete these steps to unlock RepoSage insights
            </p>
          </div>
        </div>

        <div className="space-y-3">
          {[
            { step: 1, title: "Connect a GitHub repository", done: false },
            { step: 2, title: "Run your first analysis", done: false },
            { step: 3, title: "Explore AI-generated insights", done: false },
            { step: 4, title: "Set up drift detection", done: false },
          ].map(({ step, title, done }) => (
            <div
              key={step}
              className="flex items-center gap-3 rounded-lg p-3 transition-colors hover:bg-accent/50"
            >
              <div
                className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-xs font-bold ${
                  done
                    ? "bg-emerald-500/20 text-emerald-500"
                    : "bg-muted text-muted-foreground"
                }`}
              >
                {done ? "✓" : step}
              </div>
              <span
                className={`text-sm ${
                  done
                    ? "text-muted-foreground line-through"
                    : "text-foreground"
                }`}
              >
                {title}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
