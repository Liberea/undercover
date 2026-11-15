import {
  cleanup,
  fireEvent,
  render,
  screen,
  within,
} from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import type { Run } from "./api";
import { QueueRun } from "./QueueRun";
import { stubApi } from "./testing";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

function run(overrides: Partial<Run>): Run {
  return {
    run_id: "r-1",
    cap: 5,
    status: "running",
    todos: [],
    summary: null,
    started_at: "2026-11-15T10:50:13+00:00",
    finished_at: null,
    ...overrides,
  };
}

const TODOS: Run["todos"] = [
  { content: "Work CLM-1001", status: "done" },
  { content: "Work CLM-1002", status: "left_for_handler" },
  { content: "Work CLM-1003", status: "in_progress" },
  { content: "Write the summary for the handlers", status: "to_do" },
];

it("says when there is no run yet", async () => {
  stubApi({ "GET /api/runs/latest": null });
  render(<QueueRun waiting={25} />);
  expect(await screen.findByText("No run yet.")).toBeDefined();
});

it("shows the to-do list of a running run", async () => {
  stubApi({ "GET /api/runs/latest": run({ todos: TODOS }) });
  render(<QueueRun waiting={25} />);
  const list = await screen.findByRole("list", {
    name: "The agent's to-do list",
  });
  expect(
    within(list)
      .getAllByRole("listitem")
      .map((item) => item.textContent),
  ).toEqual([
    "DoneWork CLM-1001",
    "Left for a handlerWork CLM-1002",
    "In progressWork CLM-1003",
    "To doWrite the summary for the handlers",
  ]);
  expect(screen.getByText(/up to 5 claims/).textContent).toMatch(
    /^Running, started .+, up to 5 claims$/,
  );
  expect(screen.queryByText("Summary for the handlers")).toBeNull();
});

it("shows the summary when the run is finished", async () => {
  const summary = "Decided 5 claims.\n\nTwo wait for sign-off.";
  stubApi({
    "GET /api/runs/latest": run({ status: "finished", todos: TODOS, summary }),
  });
  render(<QueueRun waiting={20} />);
  expect(await screen.findByText("Summary for the handlers")).toBeDefined();
  expect(screen.getByText(/^Decided 5 claims/).textContent).toBe(summary);
  expect(screen.getByText("Finished")).toBeDefined();
});

it("starts a run on the number of claims chosen", async () => {
  const fetchMock = stubApi({
    "POST /api/queue/agent-runs": { run_id: "r-2" },
  });
  render(<QueueRun waiting={25} />);
  const field = screen.getByLabelText("Claims");
  expect((field as HTMLInputElement).value).toBe("5");
  fireEvent.change(field, { target: { value: "3" } });
  const button = screen.getByRole("button", { name: "Work the queue" });
  fireEvent.click(button);
  expect(button.hasAttribute("disabled")).toBe(true);
  expect(fetchMock).toHaveBeenCalledWith(
    "/api/queue/agent-runs",
    expect.objectContaining({ method: "POST", body: '{"cap":3}' }),
  );
  await vi.waitFor(() => {
    expect(button.hasAttribute("disabled")).toBe(false);
  });
});

it("allows from one claim to the number waiting", () => {
  stubApi({});
  render(<QueueRun waiting={2} />);
  const field = screen.getByLabelText("Claims");
  const button = screen.getByRole("button", { name: "Work the queue" });
  expect(button.hasAttribute("disabled")).toBe(true);
  fireEvent.change(field, { target: { value: "2" } });
  expect(button.hasAttribute("disabled")).toBe(false);
  fireEvent.change(field, { target: { value: "0" } });
  expect(button.hasAttribute("disabled")).toBe(true);
});

it("says why a run could not start", async () => {
  stubApi({
    "POST /api/queue/agent-runs": Response.json(
      { detail: "The backend is busy" },
      { status: 503 },
    ),
  });
  render(<QueueRun waiting={25} />);
  fireEvent.click(screen.getByRole("button", { name: "Work the queue" }));
  expect((await screen.findByRole("alert")).textContent).toBe(
    "The backend is busy",
  );
});
