import type { Page } from "@playwright/test";

/** Dev-mode sign-in (local stack with seeded users). */
export async function signInAs(page: Page, email: string) {
  await page.goto("/sign-in");
  await page.getByRole("button", { name: email }).click();
  await page.waitForURL("**/dashboard");
}
