/**
 * src/app/App.tsx
 *
 * Root application component.
 *
 * Responsibilities:
 * - Wraps everything in the Providers tree (Query, Theme)
 * - Renders the BrowserRouter
 * - Renders the AppRouter (all route definitions)
 *
 * This component is deliberately thin — no business logic here.
 */
import { BrowserRouter } from "react-router-dom";
import { useEffect, useState } from "react";
import { Providers } from "./providers";
import { AppRouter } from "./Router";
import { useAuthStore } from "@/lib/auth-store";

export function App() {
  const initializeAuth = useAuthStore((state) => state.initializeAuth);
  const [isInitializing, setIsInitializing] = useState(true);

  useEffect(() => {
    initializeAuth().finally(() => {
      setIsInitializing(false);
    });
  }, [initializeAuth]);

  if (isInitializing) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
      </div>
    );
  }

  return (
    <BrowserRouter>
      <Providers>
        <AppRouter />
      </Providers>
    </BrowserRouter>
  );
}
