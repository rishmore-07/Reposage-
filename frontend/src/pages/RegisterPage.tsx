/**
 * src/pages/RegisterPage.tsx
 *
 * User registration page.
 */
import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Loader2 } from "lucide-react";
import { ROUTES } from "@/constants/routes";
import { useAuthStore } from "@/lib/auth-store";
import apiClient from "@/lib/api-client";
import type { TokenResponse } from "@/types/api";
import { cn } from "@/utils/cn";

export function RegisterPage() {
  const navigate = useNavigate();
  const setAuthenticated = useAuthStore((state) => state.setAuthenticated);

  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (password.length < 8) {
      setError("Password must be at least 8 characters.");
      return;
    }

    setIsLoading(true);

    try {
      await apiClient.post<TokenResponse>(
        "/api/v1/auth/register",
        { email, password, full_name: fullName || null }
      );
      setAuthenticated(true);
      navigate(ROUTES.DASHBOARD, { replace: true });
    } catch (err: unknown) {
      const message =
        (err as { response?: { data?: { message?: string } } })?.response?.data
          ?.message ?? "Registration failed. Please try again.";
      setError(message);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-background p-4">
      <div className="pointer-events-none absolute inset-0 gradient-bg" />

      <div className="relative w-full max-w-sm animate-fade-in">
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
                Create an account
              </h1>
              <p className="text-sm text-muted-foreground">
                Start analyzing your repositories today
              </p>
            </div>
          </div>

          {error && (
            <div className="mb-4 rounded-lg border border-destructive/30 bg-destructive/10 px-4 py-3 text-sm text-destructive">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4" noValidate>
            <div className="space-y-1.5">
              <label
                htmlFor="register-name"
                className="block text-sm font-medium text-foreground"
              >
                Full name{" "}
                <span className="text-muted-foreground">(optional)</span>
              </label>
              <input
                id="register-name"
                type="text"
                autoComplete="name"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                placeholder="Jane Smith"
                className={cn(
                  "block w-full rounded-lg border border-input bg-background px-3 py-2.5",
                  "text-sm text-foreground placeholder:text-muted-foreground",
                  "transition-colors focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
                )}
              />
            </div>

            <div className="space-y-1.5">
              <label
                htmlFor="register-email"
                className="block text-sm font-medium text-foreground"
              >
                Email
              </label>
              <input
                id="register-email"
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
                htmlFor="register-password"
                className="block text-sm font-medium text-foreground"
              >
                Password
              </label>
              <input
                id="register-password"
                type="password"
                autoComplete="new-password"
                required
                minLength={8}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Minimum 8 characters"
                className={cn(
                  "block w-full rounded-lg border border-input bg-background px-3 py-2.5",
                  "text-sm text-foreground placeholder:text-muted-foreground",
                  "transition-colors focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
                )}
              />
            </div>

            <button
              type="submit"
              disabled={isLoading || !email || !password}
              id="register-submit"
              className={cn(
                "flex w-full items-center justify-center gap-2 rounded-lg",
                "bg-primary px-4 py-2.5 text-sm font-semibold text-primary-foreground",
                "transition-all duration-150 hover:bg-primary/90",
                "disabled:cursor-not-allowed disabled:opacity-60",
                "shadow-md shadow-primary/25"
              )}
            >
              {isLoading && <Loader2 className="h-4 w-4 animate-spin" />}
              {isLoading ? "Creating account…" : "Create account"}
            </button>
          </form>

          <p className="mt-6 text-center text-sm text-muted-foreground">
            Already have an account?{" "}
            <Link
              to={ROUTES.LOGIN}
              className="font-medium text-primary hover:underline"
            >
              Sign in
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
