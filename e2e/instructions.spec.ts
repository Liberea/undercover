import { expect, test } from "@playwright/test";

test("the agent's instructions are shown read only", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("link", { name: "Instructions" }).click();
  await expect(
    page.getByRole("heading", { name: "The agent's instructions" }),
  ).toBeVisible();
  await expect(
    page
      .getByRole("region", { name: "Working the queue" })
      .getByText(/^You are the UnderCover Agent, running the claims queue/),
  ).toBeVisible();
  await expect(
    page
      .getByRole("region", { name: "Working a claim" })
      .getByText(/^You are the UnderCover Agent\. You decide/),
  ).toBeVisible();
  await expect(page.getByRole("textbox")).toHaveCount(0);
});
