import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./tests/e2e",
  use: { baseURL: process.env.E2E_ADMIN_URL ?? "http://localhost:3001" },
  projects: [
    {
      name: "chromium",
      // PLAYWRIGHT_CHROMIUM_PATH lets CI images with a preinstalled browser skip `playwright install`.
      use: { ...devices["Desktop Chrome"], launchOptions: { executablePath: process.env.PLAYWRIGHT_CHROMIUM_PATH || undefined } },
    },
  ],
  webServer: process.env.E2E_ADMIN_URL ? undefined : { command: "pnpm dev", url: "http://localhost:3001/sign-in", reuseExistingServer: true },
});
