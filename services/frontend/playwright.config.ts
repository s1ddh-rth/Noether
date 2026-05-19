import { defineConfig, devices } from "@playwright/test";

// Smoke E2E against a running compose stack (not started by Playwright —
// CI brings up `--profile core` first). BASE_URL points at the
// host-mapped frontend (compose maps 3001→3000).
export default defineConfig({
  testDir: "./e2e",
  timeout: 30_000,
  expect: { timeout: 10_000 },
  fullyParallel: true,
  reporter: [["list"]],
  use: {
    baseURL: process.env.BASE_URL ?? "http://localhost:3001",
    trace: "retain-on-failure",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
});
