/// <reference types="vitest" />
import path from "path";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],

  // @ts-expect-error - vitest test config
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: './src/tests/setup.ts',
  },

  // Path aliases — must match tsconfig.json paths
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },

  // Dev server configuration
  server: {
    port: 5173,
    host: "0.0.0.0", // Required for Docker bind
    // Proxy API requests to FastAPI backend (avoids CORS in development)
    proxy: {
      "/api": {
        target: process.env["VITE_API_BASE_URL"] ?? "http://localhost:8000",
        changeOrigin: true,
        // Don't rewrite — FastAPI expects /api prefix
      },
      "/health": {
        target: process.env["VITE_API_BASE_URL"] ?? "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },

  // Build configuration
  build: {
    outDir: "dist",
    sourcemap: true, // Enable for production debugging (consider disabling for security)
    // Split vendor bundles for better caching
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ["react", "react-dom"],
          router: ["react-router-dom"],
          query: ["@tanstack/react-query"],
          ui: ["lucide-react", "clsx", "tailwind-merge"],
        },
      },
    },
  },
});
