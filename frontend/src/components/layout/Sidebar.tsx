/**
 * src/components/layout/Sidebar.tsx
 *
 * Navigation sidebar with:
 * - App logo/brand
 * - Primary navigation links with active state
 * - User avatar and quick settings at the bottom
 * - Smooth hover animations
 */
import {
  BarChart3,
  BookOpen,
  Building2,
  Key,
  LayoutDashboard,
  Settings,
  type LucideIcon,
} from "lucide-react";
import { NavLink, useLocation } from "react-router-dom";
import { cn } from "@/utils/cn";
import { ROUTES } from "@/constants/routes";
import { useAuthStore } from "@/lib/auth-store";

interface NavItem {
  label: string;
  href: string;
  icon: LucideIcon;
}

const NAV_ITEMS: NavItem[] = [
  { label: "Dashboard", href: ROUTES.DASHBOARD, icon: LayoutDashboard },
  { label: "Repositories", href: ROUTES.REPOSITORIES, icon: BookOpen },
  { label: "Organizations", href: ROUTES.ORGANIZATIONS, icon: Building2 },
  { label: "Analytics", href: "/analytics", icon: BarChart3 },
  { label: "API Keys", href: ROUTES.API_KEYS, icon: Key },
  { label: "Settings", href: ROUTES.SETTINGS, icon: Settings },
];

export function Sidebar() {
  const location = useLocation();
  const user = useAuthStore((state) => state.user);

  return (
    <aside className="flex h-full w-[var(--sidebar-width)] flex-col border-r border-border bg-card/50 backdrop-blur-sm">
      {/* ── Brand ──────────────────────────────────────────────────────────── */}
      <div className="flex h-[var(--topbar-height)] items-center gap-3 border-b border-border px-5">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary">
          <span className="text-sm font-bold text-primary-foreground">RS</span>
        </div>
        <span className="gradient-text text-lg font-bold tracking-tight">
          RepoSage
        </span>
      </div>

      {/* ── Navigation ─────────────────────────────────────────────────────── */}
      <nav className="flex flex-1 flex-col gap-1 overflow-y-auto p-3">
        <div className="mb-2 px-3 py-1">
          <span className="text-xs font-semibold uppercase tracking-widest text-muted-foreground">
            Navigation
          </span>
        </div>

        {NAV_ITEMS.map((item) => {
          const Icon = item.icon;
          const isActive =
            item.href === ROUTES.DASHBOARD
              ? location.pathname === item.href
              : location.pathname.startsWith(item.href);

          return (
            <NavLink
              key={item.href}
              to={item.href}
              className={cn(
                "group flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium",
                "transition-all duration-150 ease-in-out",
                isActive
                  ? "bg-primary/10 text-primary"
                  : "text-muted-foreground hover:bg-accent hover:text-foreground"
              )}
            >
              <Icon
                className={cn(
                  "h-4 w-4 shrink-0 transition-colors",
                  isActive
                    ? "text-primary"
                    : "text-muted-foreground group-hover:text-foreground"
                )}
              />
              {item.label}
              {isActive && (
                <span className="ml-auto h-1.5 w-1.5 rounded-full bg-primary" />
              )}
            </NavLink>
          );
        })}
      </nav>

      {/* ── User section ───────────────────────────────────────────────────── */}
      <div className="border-t border-border p-3">
        <div className="flex items-center gap-3 rounded-lg p-2">
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary/20 text-xs font-bold text-primary">
            {user?.full_name?.charAt(0)?.toUpperCase() ??
              user?.email?.charAt(0)?.toUpperCase() ??
              "U"}
          </div>
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-medium text-foreground">
              {user?.full_name ?? user?.email ?? "User"}
            </p>
            <p className="truncate text-xs text-muted-foreground">
              {user?.email ?? ""}
            </p>
          </div>
        </div>
      </div>
    </aside>
  );
}
