import { expect, test } from "@playwright/test";

test("the queue lists every claim and where it stands", async ({ page }) => {
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "Claims queue" }),
  ).toBeVisible();
  await expect(page.getByText("25 claims")).toBeVisible();
  await expect(page.getByRole("row")).toHaveCount(26);
  await expect(
    page
      .getByRole("list", { name: "Where the claims stand" })
      .getByRole("listitem"),
  ).toHaveText([
    /Waiting$/,
    /In progress$/,
    /Waiting for sign-off$/,
    /Decided$/,
  ]);
  const row = page.getByRole("row").filter({ hasText: "CLM-1001" });
  await expect(row).toContainText("Maya Patel");
  await expect(row).toContainText("$420.00");
  await expect(row).toContainText("Waiting");
});

test("a claim in the queue opens its page", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("link", { name: "CLM-1001" }).click();
  await expect(page).toHaveURL(/#\/claims\/CLM-1001$/);
  await expect(page.getByRole("heading", { name: "CLM-1001" })).toBeVisible();
});
