/**
 * src/constants/routes.ts
 *
 * Typed route path constants.
 * All navigation must use these constants — no magic strings.
 * Typos become TypeScript compile errors.
 */
export const ROUTES = {
  // Public routes
  HOME: "/",
  LOGIN: "/login",
  REGISTER: "/register",

  // Authenticated routes
  DASHBOARD: "/dashboard",
  REPOSITORIES: "/repositories",
  REPOSITORY_DETAIL: (id: string) => `/repositories/${id}` as const,
  ORGANIZATIONS: "/organizations",
  ORGANIZATION_DETAIL: (id: string) => `/organizations/${id}` as const,
  SETTINGS: "/settings",
  API_KEYS: "/settings/api-keys",
  PROFILE: "/settings/profile",

  // Error routes
  NOT_FOUND: "/404",
  ERROR: "/error",
} as const;

/** Route path for React Router pattern matching (with :param syntax) */
export const ROUTE_PATTERNS = {
  REPOSITORY_DETAIL: "/repositories/:repositoryId",
  ORGANIZATION_DETAIL: "/organizations/:organizationId",
} as const;
