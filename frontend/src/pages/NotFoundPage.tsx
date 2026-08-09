/**
 * src/pages/NotFoundPage.tsx
 *
 * 404 Not Found page — shown for any unmatched route.
 */
import { Home } from "lucide-react";
import { Link } from "react-router-dom";
import { ROUTES } from "@/constants/routes";

export function NotFoundPage() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-background p-4 text-center">
      <div className="pointer-events-none absolute inset-0 gradient-bg" />

      <div className="relative animate-fade-in">
        {/* Error code */}
        <p className="gradient-text text-9xl font-black tracking-tighter">
          404
        </p>

        {/* Message */}
        <h1 className="mt-4 text-2xl font-bold text-foreground">
          Page not found
        </h1>
        <p className="mt-2 max-w-sm text-muted-foreground">
          The page you're looking for doesn't exist or has been moved.
        </p>

        {/* Action */}
        <Link
          to={ROUTES.DASHBOARD}
          id="not-found-home-link"
          className="mt-8 inline-flex items-center gap-2 rounded-lg bg-primary px-5 py-2.5 text-sm font-semibold text-primary-foreground shadow-lg shadow-primary/25 transition-all hover:bg-primary/90"
        >
          <Home className="h-4 w-4" />
          Back to Dashboard
        </Link>
      </div>
    </div>
  );
}
