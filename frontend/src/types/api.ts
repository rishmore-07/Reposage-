/**
 * src/types/api.ts
 *
 * Shared TypeScript types for API communication.
 * These types mirror the Pydantic schemas defined in the backend.
 */

/** Generic paginated API response */
export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

/** Structured API error response from the backend */
export interface ApiError {
  error_code: string;
  message: string;
  status_code: number;
}

/** Simple message response */
export interface MessageResponse {
  message: string;
}

/** JWT token pair */
export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

/** Application health check response */
export interface HealthResponse {
  status: "ok" | "degraded" | "down";
  version: string;
  environment: string;
  database: string;
}
