/**
 * src/test/setup.ts
 *
 * Vitest test setup file.
 * Imported by all test files via vite.config.ts setupFiles.
 */

// Future: import '@testing-library/jest-dom' here for extended DOM matchers
// import '@testing-library/jest-dom';

// Mock localStorage for tests that use auth store
const localStorageMock = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: (key: string) => store[key] ?? null,
    setItem: (key: string, value: string) => {
      store[key] = value;
    },
    removeItem: (key: string) => {
      // eslint-disable-next-line @typescript-eslint/no-dynamic-delete
      delete store[key];
    },
    clear: () => {
      store = {};
    },
  };
})();

Object.defineProperty(window, "localStorage", {
  value: localStorageMock,
});
