import { expect, test } from "@playwright/test";
import { signInAs } from "./helpers";

test("auditor sees read-only navigation", async ({ page }) => {
  await signInAs(page, "auditor@demo.test");
  await expect(page.getByRole("link", { name: "Audit log" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Ask the Rules" })).toHaveCount(0);
  await page.goto("/clients");
  await expect(page.getByRole("link", { name: "New client" })).toHaveCount(0);
});

test("staff cannot open the audit log", async ({ page }) => {
  await signInAs(page, "staff@demo.test");
  await expect(page.getByRole("link", { name: "Audit log" })).toHaveCount(0);
  await page.goto("/audit-log");
  await expect(page.getByText(/not available/i)).toBeVisible();
});
