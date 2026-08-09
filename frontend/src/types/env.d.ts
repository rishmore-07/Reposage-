/**
 * src/types/env.d.ts
 *
 * Vite environment variable type declarations.
 * Ensures VITE_* variables are typed and IDE-autocompleted.
 */

/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Backend API base URL (e.g., "http://localhost:8000") */
  readonly VITE_API_BASE_URL: string;
  /** Application name for display */
  readonly VITE_APP_NAME: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
