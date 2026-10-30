import { expect, test } from "@playwright/test";

test("super admin sees tenants and system health", async ({ page }) => {
  await page.goto("/sign-in");
  await page.getByLabel("Email").fill("admin@complymate.test");
  await page.getByRole("button", { name: "Sign in" }).click();
  await page.waitForURL("**/tenants");
  await expect(page.getByRole("heading", { name: "Tenants" })).toBeVisible();
  await page.getByRole("link", { name: "System health" }).click();
  await expect(page.getByText(/database/i)).toBeVisible();
});
