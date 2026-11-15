import { expect, test } from "@playwright/test";

function todos(first: string, second: string) {
  return {
    data: {
      todos: [
        { content: "Work CLM-1004", status: first },
        { content: "Write the summary for the handlers", status: second },
      ],
    },
  };
}

// Tests never call a model, so this test plays the queue agent's part through
// the API while the queue page shows what a handler sees.
test("the queue page follows the agent's run", async ({ page, request }) => {
  await page.goto("/");
  await expect(page.getByText("No run yet.")).toBeVisible();

  await request.post("/api/runs", { data: { run_id: "e2e-run", cap: 2 } });
  await request.put("/api/runs/e2e-run/todos", todos("to_do", "to_do"));
  const items = page
    .getByRole("list", { name: "The agent's to-do list" })
    .getByRole("listitem");
  await expect(items).toHaveText([
    "To doWork CLM-1004",
    "To doWrite the summary for the handlers",
  ]);
  await expect(
    page.getByText(/^Running, started .+, up to 2 claims$/),
  ).toBeVisible();

  await request.put("/api/runs/e2e-run/todos", todos("in_progress", "to_do"));
  await expect(items.first()).toHaveText("In progressWork CLM-1004");
  await request.put("/api/runs/e2e-run/todos", todos("done", "done"));
  await expect(items).toHaveText([
    "DoneWork CLM-1004",
    "DoneWrite the summary for the handlers",
  ]);

  await request.post("/api/runs/e2e-run/finish", {
    data: { summary: "Declined CLM-1004." },
  });
  await expect(page.getByText("Summary for the handlers")).toBeVisible();
  await expect(page.getByText("Declined CLM-1004.")).toBeVisible();
  await expect(page.getByText(/^Finished, started/)).toBeVisible();
});
