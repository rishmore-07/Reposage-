/**
 * src/app/Router.tsx
 *
 * Application route definitions.
 *
 * Structure:
 * - Public routes (login, register) — accessible without authentication
 * - Protected routes — wrapped in ProtectedRoute, redirect to /login if not authenticated
 * - The AppShell layout wraps all authenticated routes (sidebar + topbar)
 *
 * Adding a new page:
 * 1. Create src/pages/NewPage.tsx
 * 2. Add a <Route> inside the protected routes section
 * 3. Add the path to src/constants/routes.ts
 */
import { Navigate, Route, Routes } from "react-router-dom";
import { AppShell } from "@/components/layout/AppShell";
import { ProtectedRoute } from "@/components/routing/ProtectedRoute";
import { ROUTES } from "@/constants/routes";

// Pages
import { DashboardPage } from "@/pages/DashboardPage";
import { ErrorPage } from "@/pages/ErrorPage";
import { LoginPage } from "@/pages/LoginPage";
import { NotFoundPage } from "@/pages/NotFoundPage";
import { RegisterPage } from "@/pages/RegisterPage";
import { RepositoriesPage } from "@/pages/RepositoriesPage";

export function AppRouter() {
  return (
    <Routes>
      {/* ── Public routes ────────────────────────────────────────────── */}
      <Route path={ROUTES.LOGIN} element={<LoginPage />} />
      <Route path={ROUTES.REGISTER} element={<RegisterPage />} />

      {/* ── Error pages (public) ─────────────────────────────────────── */}
      <Route path={ROUTES.ERROR} element={<ErrorPage />} />
      <Route path={ROUTES.NOT_FOUND} element={<NotFoundPage />} />

      {/* ── Protected routes ─────────────────────────────────────────── */}
      {/* AppShell wraps all authenticated pages (sidebar + topbar) */}
      <Route
        element={
          <ProtectedRoute>
            <AppShell />
          </ProtectedRoute>
        }
      >
        {/* Default redirect: / → /dashboard */}
        <Route path={ROUTES.HOME} element={<Navigate to={ROUTES.DASHBOARD} replace />} />

        {/* Main application pages */}
        <Route path={ROUTES.DASHBOARD} element={<DashboardPage />} />
        <Route path={ROUTES.REPOSITORIES} element={<RepositoriesPage />} />
      </Route>

      {/* ── 404 catch-all ────────────────────────────────────────────── */}
      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  );
}
