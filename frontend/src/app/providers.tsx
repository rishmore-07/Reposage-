/**
 * src/app/providers.tsx
 *
 * Root provider tree for the application.
 *
 * All global context providers are composed here.
 * App.tsx renders this once — all child components have access
 * to query client, theme, and auth state without prop drilling.
 */
import { QueryClientProvider } from "@tanstack/react-query";
import { ReactQueryDevtools } from "@tanstack/react-query-devtools";
import type { ReactNode } from "react";
import { ThemeProvider } from "@/components/theme/ThemeProvider";
import { queryClient } from "@/lib/query-client";

interface ProvidersProps {
  children: ReactNode;
}

export function Providers({ children }: ProvidersProps) {
  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider defaultTheme="dark" storageKey="reposage-theme">
        {children}
      </ThemeProvider>
      {/* React Query Devtools — only included in development builds */}
      <ReactQueryDevtools initialIsOpen={false} />
    </QueryClientProvider>
  );
}
