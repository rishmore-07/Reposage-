/**
 * src/pages/ErrorPage.tsx
 *
 * Generic error page for unhandled application errors.
 * Can be shown by React Router's errorElement or navigated to directly.
 */
import { AlertTriangle, RefreshCw } from "lucide-react";
import { Link } from "react-router-dom";
import { ROUTES } from "@/constants/routes";

export function ErrorPage() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-background p-4 text-center">
      <div className="pointer-events-none absolute inset-0 gradient-bg" />

      <div className="relative animate-fade-in max-w-md">
        {/* Icon */}
        <div className="mb-6 flex justify-center">
          <div className="flex h-20 w-20 items-center justify-center rounded-2xl bg-destructive/10 ring-1 ring-destructive/20">
            <AlertTriangle className="h-10 w-10 text-destructive" />
          </div>
        </div>

        {/* Message */}
        <h1 className="text-2xl font-bold text-foreground">
          Something went wrong
        </h1>
        <p className="mt-3 text-muted-foreground">
          An unexpected error occurred. Our team has been notified. Please
          try refreshing the page or returning to the dashboard.
        </p>

        {/* Actions */}
        <div className="mt-8 flex flex-col gap-3 sm:flex-row sm:justify-center">
          <button
            id="error-refresh-button"
            onClick={() => window.location.reload()}
            className="inline-flex items-center justify-center gap-2 rounded-lg bg-primary px-5 py-2.5 text-sm font-semibold text-primary-foreground shadow-md shadow-primary/25 transition-all hover:bg-primary/90"
          >
            <RefreshCw className="h-4 w-4" />
            Refresh page
          </button>
          <Link
            to={ROUTES.DASHBOARD}
            id="error-dashboard-link"
            className="inline-flex items-center justify-center rounded-lg border border-border px-5 py-2.5 text-sm font-medium text-foreground transition-colors hover:bg-accent"
          >
            Go to Dashboard
          </Link>
        </div>
      </div>
    </div>
  );
}
