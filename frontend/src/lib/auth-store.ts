/**
 * src/lib/auth-store.ts
 *
 * Zustand store for authentication state.
 *
 * Design decisions:
 * - Tokens are stored securely in HttpOnly cookies (not in localStorage)
 * - User object is stored in memory and persisted (re-fetched on app load for safety)
 * - The store is the single source of truth for "is user logged in?"
 */
import { create } from "zustand";
import { persist } from "zustand/middleware";

export interface AuthUser {
  id: string;
  email: string;
  full_name: string | null;
  avatar_url: string | null;
  github_username: string | null;
  is_active: boolean;
  is_email_verified: boolean;
  is_superuser: boolean;
}

interface AuthState {
  // User state
  user: AuthUser | null;

  // Derived: true if the user is authenticated
  isAuthenticated: boolean;

  // Actions
  setAuthenticated: (status: boolean) => void;
  setUser: (user: AuthUser | null) => void;
  logout: () => void;
  initializeAuth: () => Promise<void>;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      isAuthenticated: false,

      setAuthenticated: (status: boolean) => {
        set({ isAuthenticated: status });
      },

      setUser: (user: AuthUser | null) => {
        set({ user, isAuthenticated: user !== null });
      },

      logout: () => {
        set({
          user: null,
          isAuthenticated: false,
        });
      },

      initializeAuth: async () => {
        try {
          const { default: apiClient } = await import("./api-client");
          const response = await apiClient.get<AuthUser>("/api/v1/users/me");
          set({ user: response.data, isAuthenticated: true });
        } catch {
          // If unauthenticated or network error, reset state
          set({ user: null, isAuthenticated: false });
        }
      },
    }),
    {
      name: "reposage-auth",
      // We persist the user object to avoid UI flicker on reload,
      // but the API dictates actual auth validity via cookies.
      partialize: (state) => ({
        user: state.user,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
);
