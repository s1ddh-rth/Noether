import react from "@vitejs/plugin-react";
import { resolve } from "node:path";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: { "@": resolve(__dirname, ".") },
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./vitest.setup.ts"],
    include: ["**/*.test.ts", "**/*.test.tsx"],
    coverage: {
      provider: "v8",
      include: ["components/**/*.tsx"],
      exclude: ["**/*.test.tsx"],
      reporter: ["text", "html"],
      // tasks.md §6.4 — ≥70% on components/.
      thresholds: { lines: 70, functions: 70, statements: 70, branches: 70 },
    },
  },
});
