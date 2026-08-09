/**
 * src/lib/api-client.ts
 *
 * Axios instance configured for the RepoSage API.
 *
 * Responsibilities:
 * - Sets the base URL from environment variables
 * - Sends HttpOnly cookies with every request via withCredentials
 * - Handles 401 responses by redirecting to login
 * - Parses API errors into a consistent ApiError shape
 *
 * All feature API modules import this instance — never create new Axios instances.
 */
import axios, {
  type AxiosError,
  type AxiosInstance,
  type AxiosResponse,
} from "axios";

// ── API Error type ─────────────────────────────────────────────────────────────

export interface ApiError {
  error_code: string;
  message: string;
  status_code: number;
}

// ── Axios instance ─────────────────────────────────────────────────────────────

const apiClient: AxiosInstance = axios.create({
  baseURL: import.meta.env["VITE_API_BASE_URL"] ?? "",
  timeout: 30_000, // 30 second timeout
  withCredentials: true,
  headers: {
    "Content-Type": "application/json",
    Accept: "application/json",
  },
});

// ── Response interceptor: handle auth errors ───────────────────────────────────

apiClient.interceptors.response.use(
  (response: AxiosResponse) => response,
  async (error: AxiosError<ApiError>) => {
    if (error.response?.status === 401) {
      // Redirect to login if unauthorized
      window.location.href = "/login";
    }
    return Promise.reject(error);
  }
);

export default apiClient;

// ── Helper: extract ApiError from Axios errors ─────────────────────────────────

export function getApiError(error: unknown): ApiError {
  if (axios.isAxiosError(error) && error.response?.data) {
    const data = error.response.data as Partial<ApiError>;
    return {
      error_code: data.error_code ?? "unknown_error",
      message: data.message ?? "An unexpected error occurred.",
      status_code: data.status_code ?? error.response.status,
    };
  }
  return {
    error_code: "network_error",
    message: "Unable to connect to the server. Please check your connection.",
    status_code: 0,
  };
}
