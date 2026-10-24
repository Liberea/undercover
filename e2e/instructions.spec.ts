import { expect, test } from "@playwright/test";

test("the agent's instructions are shown read only", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("link", { name: "Instructions" }).click();
  await expect(
    page.getByRole("heading", { name: "The agent's instructions" }),
  ).toBeVisible();
  await expect(page.getByText(/^You are the UnderCover Agent\./)).toBeVisible();
  await expect(page.getByRole("textbox")).toHaveCount(0);
});
