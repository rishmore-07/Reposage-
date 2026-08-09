/**
 * src/components/routing/ProtectedRoute.tsx
 *
 * Route guard for authenticated pages.
 *
 * Checks if the user has a stored access token.
 * If not authenticated → redirects to /login with the intended destination
 * preserved in location state (so the user lands on the right page after login).
 *
 * Usage in Router.tsx:
 *   <Route element={<ProtectedRoute><AppShell /></ProtectedRoute>}>
 *     <Route path="/dashboard" element={<DashboardPage />} />
 *   </Route>
 */
import type { ReactNode } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { ROUTES } from "@/constants/routes";
import { useAuthStore } from "@/lib/auth-store";

interface ProtectedRouteProps {
  children: ReactNode;
}

export function ProtectedRoute({ children }: ProtectedRouteProps) {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);
  const location = useLocation();

  if (!isAuthenticated) {
    // Preserve the intended destination so we can redirect after login
    return (
      <Navigate
        to={ROUTES.LOGIN}
        state={{ from: location.pathname }}
        replace
      />
    );
  }

  return <>{children}</>;
}
