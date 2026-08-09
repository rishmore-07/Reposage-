/**
 * src/components/layout/AppShell.tsx
 *
 * Main authenticated layout wrapper.
 * Renders the Sidebar + TopBar and an <Outlet /> for page content.
 *
 * Used as the layout element for all protected routes in Router.tsx:
 *   <Route element={<ProtectedRoute><AppShell /></ProtectedRoute>}>
 *     <Route path="/dashboard" element={<DashboardPage />} />
 *   </Route>
 */
import { Outlet } from "react-router-dom";
import { Sidebar } from "./Sidebar";
import { TopBar } from "./TopBar";

export function AppShell() {
  return (
    <div className="flex h-screen w-full overflow-hidden bg-background">
      {/* Sidebar — fixed width, full height */}
      <Sidebar />

      {/* Main content area — fills remaining space */}
      <div className="flex flex-1 flex-col overflow-hidden">
        {/* Top bar — fixed height */}
        <TopBar />

        {/* Page content — scrollable */}
        <main className="flex-1 overflow-y-auto">
          {/* gradient-bg adds a subtle ambient glow to every page */}
          <div className="gradient-bg min-h-full">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
}
