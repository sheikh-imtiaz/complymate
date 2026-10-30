import { expect, test } from "@playwright/test";

test("new firm sign-up runs the designated services check", async ({ page }) => {
  const email = `founder.${Date.now()}@e2e.test`;
  await page.goto("/sign-up");
  await page.getByLabel("Work email").fill(email);
  await page.getByRole("button", { name: /get started/i }).click();
  await page.waitForURL("**/onboarding");
  await page.getByLabel("Firm name").fill("E2E Conveyancing Pty Ltd");
  await page.getByRole("button", { name: "Next" }).click();
  await page.getByText(/buy, sell or transfer real estate/i).click();
  await page.getByRole("button", { name: /check obligations/i }).click();
  await expect(page.getByText(/obligations likely apply/i)).toBeVisible();
  await page.getByRole("button", { name: /create firm/i }).click();
  await page.waitForURL("**/admin/users**");
  await expect(page.getByText(/nominate your aml\/ctf compliance officer/i)).toBeVisible();
});
