/**
 * src/components/layout/TopBar.tsx
 *
 * Application top bar with:
 * - Page title (dynamic via usePageTitle context)
 * - Notification bell
 * - Theme toggle
 * - User dropdown menu
 */
import { Bell, LogOut, Moon, Settings, Sun } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { ROUTES } from "@/constants/routes";
import { useAuthStore } from "@/lib/auth-store";
import { useTheme } from "@/components/theme/ThemeProvider";
import { cn } from "@/utils/cn";

export function TopBar() {
  const { theme, setTheme } = useTheme();
  const logout = useAuthStore((state) => state.logout);
  const user = useAuthStore((state) => state.user);
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate(ROUTES.LOGIN, { replace: true });
  };

  const toggleTheme = () => {
    setTheme(theme === "dark" ? "light" : "dark");
  };

  return (
    <header
      className={cn(
        "flex h-[var(--topbar-height)] items-center justify-between",
        "border-b border-border bg-card/50 px-6 backdrop-blur-sm"
      )}
    >
      {/* ── Left: Breadcrumb / page title (slot for page-level content) ──── */}
      <div className="flex items-center gap-2" id="topbar-left">
        {/* Pages inject their title via CSS or a context — this is the mount point */}
      </div>

      {/* ── Right: Actions ─────────────────────────────────────────────────── */}
      <div className="flex items-center gap-1">
        {/* Theme toggle */}
        <button
          onClick={toggleTheme}
          aria-label="Toggle theme"
          className={cn(
            "flex h-9 w-9 items-center justify-center rounded-lg",
            "text-muted-foreground transition-all duration-150",
            "hover:bg-accent hover:text-foreground"
          )}
        >
          {theme === "dark" ? (
            <Sun className="h-4 w-4" />
          ) : (
            <Moon className="h-4 w-4" />
          )}
        </button>

        {/* Notification bell */}
        <button
          aria-label="Notifications"
          className={cn(
            "relative flex h-9 w-9 items-center justify-center rounded-lg",
            "text-muted-foreground transition-all duration-150",
            "hover:bg-accent hover:text-foreground"
          )}
        >
          <Bell className="h-4 w-4" />
          {/* Unread badge — shown when there are unread notifications */}
          <span className="absolute right-1.5 top-1.5 h-2 w-2 rounded-full bg-primary" />
        </button>

        {/* Divider */}
        <div className="mx-2 h-5 w-px bg-border" />

        {/* User menu */}
        <div className="relative group">
          <button
            aria-label="User menu"
            className={cn(
              "flex h-9 items-center gap-2.5 rounded-lg px-2",
              "text-sm font-medium text-foreground transition-all duration-150",
              "hover:bg-accent"
            )}
          >
            {user?.avatar_url ? (
              <img src={user.avatar_url} alt="Avatar" className="h-7 w-7 rounded-full object-cover border border-border" />
            ) : (
              <div className="flex h-7 w-7 items-center justify-center rounded-full bg-primary/20 text-xs font-bold text-primary">
                {user?.full_name?.charAt(0)?.toUpperCase() ??
                  user?.email?.charAt(0)?.toUpperCase() ??
                  "U"}
              </div>
            )}
            <span className="hidden sm:inline-block max-w-[120px] truncate">
              {user?.full_name ?? user?.email ?? "User"}
            </span>
          </button>

          {/* Dropdown menu */}
          <div
            className={cn(
              "absolute right-0 top-full z-50 mt-1 min-w-[180px]",
              "rounded-lg border border-border bg-popover shadow-lg",
              "opacity-0 scale-95 pointer-events-none",
              "group-focus-within:opacity-100 group-focus-within:scale-100 group-focus-within:pointer-events-auto",
              "transition-all duration-150 origin-top-right"
            )}
          >
            <div className="p-1">
              <button
                onClick={() => navigate(ROUTES.SETTINGS)}
                className="flex w-full items-center gap-2.5 rounded-md px-3 py-2 text-sm text-foreground hover:bg-accent transition-colors"
              >
                <Settings className="h-3.5 w-3.5 text-muted-foreground" />
                Settings
              </button>
              <button
                onClick={handleLogout}
                className="flex w-full items-center gap-2.5 rounded-md px-3 py-2 text-sm text-destructive hover:bg-destructive/10 transition-colors"
              >
                <LogOut className="h-3.5 w-3.5" />
                Sign out
              </button>
            </div>
          </div>
        </div>
      </div>
    </header>
  );
}
