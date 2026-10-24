import { expect, test } from "@playwright/test";

// Tests never call a model, so this test plays the agent's part through the
// API while the page shows what a handler sees.
test("a handler follows the agent and signs off a payout over the limit", async ({
  page,
  request,
}) => {
  const api = "/api/claims/CLM-1002";
  await page.goto(`/#/claims/CLM-1002`);
  await expect(
    page.getByRole("button", { name: "Run the agent" }),
  ).toBeVisible();

  await request.post(`${api}/start`, { data: { thread_id: "e2e" } });
  await request.post(`${api}/steps`, {
    data: { thread_id: "e2e", kind: "tool_call", text: "get_claim({})" },
  });
  await expect(page.getByText("In progress")).toBeVisible();
  await expect(page.getByText("get_claim({})")).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Run the agent" }),
  ).toBeHidden();

  await request.post(`${api}/decision`, {
    data: {
      outcome: "approve",
      payout: 1150,
      reasons: "The bag was lost by the airline.",
      policy_section: "Section 5, Baggage and Personal Effects",
    },
  });
  const payment = await request.post(`${api}/payment`, {
    data: { amount: 1150 },
  });
  expect(payment.status()).toBe(403);
  await expect(page.getByText("Waiting for sign-off")).toBeVisible();
  await expect(
    page.getByText("The payment waits for a handler's sign-off."),
  ).toBeVisible();

  await page.getByLabel("Handler").selectOption({ label: "Dana Whitfield" });
  await page.getByRole("button", { name: "Sign off and pay" }).click();
  await expect(
    page.getByText("Paid $1,150.00, signed off by Dana Whitfield"),
  ).toBeVisible();
  await expect(page.getByText("Decided")).toBeVisible();
});
