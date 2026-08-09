/**
 * src/pages/LoginPage.tsx
 *
 * Login page with email/password form.
 * On success: stores tokens in auth store and navigates to intended destination.
 */
import { useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { Eye, EyeOff, Loader2 } from "lucide-react";
import { ROUTES } from "@/constants/routes";
import { useAuthStore } from "@/lib/auth-store";
import apiClient from "@/lib/api-client";
import type { TokenResponse } from "@/types/api";
import { cn } from "@/utils/cn";

export function LoginPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const setAuthenticated = useAuthStore((state) => state.setAuthenticated);

  // Where to go after login (preserved by ProtectedRoute)
  const from =
    (location.state as { from?: string } | null)?.from ?? ROUTES.DASHBOARD;

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsLoading(true);

    try {
      await apiClient.post<TokenResponse>(
        "/api/v1/auth/login",
        { email, password }
      );
      // Auth state is now managed securely via HttpOnly cookies
      setAuthenticated(true);
      navigate(from, { replace: true });
    } catch (err: unknown) {
      const message =
        (err as { response?: { data?: { message?: string } } })?.response?.data
          ?.message ?? "Invalid email or password.";
      setError(message);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-background p-4">
      {/* Background glow */}
      <div className="pointer-events-none absolute inset-0 gradient-bg" />

      <div className="relative w-full max-w-sm animate-fade-in">
        {/* Card */}
        <div className="glass-card rounded-2xl p-8 shadow-2xl">
          {/* Logo */}
          <div className="mb-8 flex flex-col items-center gap-3">
            <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-primary shadow-lg shadow-primary/25">
              <span className="text-lg font-bold text-primary-foreground">
                RS
              </span>
            </div>
            <div className="text-center">
              <h1 className="text-xl font-bold text-foreground">
                Welcome back
              </h1>
              <p className="text-sm text-muted-foreground">
                Sign in to RepoSage
              </p>
            </div>
          </div>

          {/* Error alert */}
          {error && (
            <div className="mb-4 rounded-lg border border-destructive/30 bg-destructive/10 px-4 py-3 text-sm text-destructive">
              {error}
            </div>
          )}

          {/* GitHub OAuth Button */}
          <button
            type="button"
            onClick={() => {
              window.location.href = "http://localhost:8000/api/v1/auth/github/login";
            }}
            className={cn(
              "mb-4 flex w-full items-center justify-center gap-3 rounded-lg border border-input",
              "bg-background px-4 py-2.5 text-sm font-semibold text-foreground",
              "transition-all duration-150 hover:bg-muted"
            )}
          >
            <svg viewBox="0 0 24 24" className="h-5 w-5" fill="currentColor">
              <path d="M12 .297c-6.63 0-12 5.373-12 12 0 5.303 3.438 9.8 8.205 11.385.6.113.82-.258.82-.577 0-.285-.01-1.04-.015-2.04-3.338.724-4.042-1.61-4.042-1.61C4.422 18.07 3.633 17.7 3.633 17.7c-1.087-.744.084-.729.084-.729 1.205.084 1.838 1.236 1.838 1.236 1.07 1.835 2.809 1.305 3.495.998.108-.776.417-1.305.76-1.605-2.665-.3-5.466-1.332-5.466-5.93 0-1.31.465-2.38 1.235-3.22-.135-.303-.54-1.523.105-3.176 0 0 1.005-.322 3.3 1.23.96-.267 1.98-.399 3-.405 1.02.006 2.04.138 3 .405 2.28-1.552 3.285-1.23 3.285-1.23.645 1.653.24 2.873.12 3.176.765.84 1.23 1.91 1.23 3.22 0 4.61-2.805 5.625-5.475 5.92.42.36.81 1.096.81 2.22 0 1.606-.015 2.896-.015 3.286 0 .315.21.69.825.57C20.565 22.092 24 17.592 24 12.297c0-6.627-5.373-12-12-12" />
            </svg>
            Continue with GitHub
          </button>

          <div className="relative mb-4 flex items-center py-2">
            <div className="flex-grow border-t border-muted"></div>
            <span className="flex-shrink-0 px-4 text-xs text-muted-foreground uppercase">Or</span>
            <div className="flex-grow border-t border-muted"></div>
          </div>

          {/* Form */}
          <form onSubmit={handleSubmit} className="space-y-4" noValidate>
            <div className="space-y-1.5">
              <label
                htmlFor="login-email"
                className="block text-sm font-medium text-foreground"
              >
                Email
              </label>
              <input
                id="login-email"
                type="email"
                autoComplete="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@company.com"
                className={cn(
                  "block w-full rounded-lg border border-input bg-background px-3 py-2.5",
                  "text-sm text-foreground placeholder:text-muted-foreground",
                  "transition-colors focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
                )}
              />
            </div>

            <div className="space-y-1.5">
              <label
                htmlFor="login-password"
                className="block text-sm font-medium text-foreground"
              >
                Password
              </label>
              <div className="relative">
                <input
                  id="login-password"
                  type={showPassword ? "text" : "password"}
                  autoComplete="current-password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  className={cn(
                    "block w-full rounded-lg border border-input bg-background px-3 py-2.5 pr-10",
                    "text-sm text-foreground placeholder:text-muted-foreground",
                    "transition-colors focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
                  )}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((v) => !v)}
                  aria-label={showPassword ? "Hide password" : "Show password"}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors"
                >
                  {showPassword ? (
                    <EyeOff className="h-4 w-4" />
                  ) : (
                    <Eye className="h-4 w-4" />
                  )}
                </button>
              </div>
            </div>

            <button
              type="submit"
              disabled={isLoading || !email || !password}
              id="login-submit"
              className={cn(
                "flex w-full items-center justify-center gap-2 rounded-lg",
                "bg-primary px-4 py-2.5 text-sm font-semibold text-primary-foreground",
                "transition-all duration-150 hover:bg-primary/90",
                "disabled:cursor-not-allowed disabled:opacity-60",
                "shadow-md shadow-primary/25"
              )}
            >
              {isLoading && <Loader2 className="h-4 w-4 animate-spin" />}
              {isLoading ? "Signing in…" : "Sign in"}
            </button>
          </form>

          {/* Footer */}
          <p className="mt-6 text-center text-sm text-muted-foreground">
            Don't have an account?{" "}
            <Link
              to={ROUTES.REGISTER}
              className="font-medium text-primary hover:underline"
            >
              Create one
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
