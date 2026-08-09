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
import { Providers } from "./providers";
import { AppRouter } from "./Router";

export function App() {
  return (
    <BrowserRouter>
      <Providers>
        <AppRouter />
      </Providers>
    </BrowserRouter>
  );
}
