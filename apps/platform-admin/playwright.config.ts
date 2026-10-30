import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./tests/e2e",
  use: { baseURL: process.env.E2E_ADMIN_URL ?? "http://localhost:3001" },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: process.env.E2E_ADMIN_URL ? undefined : { command: "pnpm dev", url: "http://localhost:3001/sign-in", reuseExistingServer: true },
});
