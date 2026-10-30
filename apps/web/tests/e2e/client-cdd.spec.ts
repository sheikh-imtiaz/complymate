import { expect, test } from "@playwright/test";
import { signInAs } from "./helpers";

test("staff onboard a client, screen and assess risk", async ({ page }) => {
  await signInAs(page, "staff@demo.test");
  await page.goto("/clients/new");
  await page.getByLabel("Given names").fill("Erin");
  await page.getByLabel("Family name").fill(`Example${Date.now() % 10000}`);
  await page.getByLabel("Residential country").fill("AU");
  await page.getByRole("button", { name: "Save client" }).click();
  await page.waitForURL("**/owners");
  await page.getByRole("link", { name: "Screening" }).click();
  await page.getByRole("button", { name: "Run screening now" }).click();
  await expect(page.getByText(/manual/i).first()).toBeVisible();
  await page.getByRole("link", { name: "Risk" }).click();
  await page.getByRole("button", { name: "Run risk assessment" }).click();
  await expect(page.getByText(/risk/i).first()).toBeVisible();
});
