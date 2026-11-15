import { expect, test } from "@playwright/test";

// Tests never call a model, so this test plays two failed runs through the API.
test("a claim that fails twice is left for a handler", async ({
  page,
  request,
}) => {
  const api = "/api/claims/CLM-1015";
  for (const thread of ["e2e-1", "e2e-2"]) {
    await request.post(`${api}/start`, { data: { thread_id: thread } });
    await request.post(`${api}/release`);
  }

  await page.goto("/");
  const row = page.getByRole("row").filter({ hasText: "CLM-1015" });
  await expect(row).toContainText("Left for a handler");

  await row.getByRole("link", { name: "CLM-1015" }).click();
  await expect(
    page.getByText(
      "The agent failed on this claim twice, so it is left for a handler.",
    ),
  ).toBeVisible();
  await expect(page.getByRole("button", { name: "Run the agent" })).toHaveCount(
    0,
  );
});
