import { defineConfig, devices } from "@playwright/test";

// E2E runs against the local stack (make up && make api && make seed). CI starts them in the e2e job.
export default defineConfig({
  testDir: "./tests/e2e",
  timeout: 60_000,
  retries: process.env.CI ? 2 : 0,
  use: { baseURL: process.env.E2E_BASE_URL ?? "http://localhost:3000", trace: "on-first-retry" },
  projects: [
    {
      name: "chromium",
      // PLAYWRIGHT_CHROMIUM_PATH lets CI images with a preinstalled browser skip `playwright install`.
      use: { ...devices["Desktop Chrome"], launchOptions: { executablePath: process.env.PLAYWRIGHT_CHROMIUM_PATH || undefined } },
    },
  ],
  webServer: process.env.E2E_BASE_URL
    ? undefined
    : { command: "pnpm dev", url: "http://localhost:3000/api/health", reuseExistingServer: true, timeout: 120_000 },
});
