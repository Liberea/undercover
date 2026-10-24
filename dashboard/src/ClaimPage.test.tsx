import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import type { Claim, Step } from "./api";
import { ClaimPage } from "./ClaimPage";
import { APPROVAL, RECORDS, claim, stubApi } from "./testing";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

function show(shown: Claim, steps: Step[] = [], more = {}) {
  const fetchMock = stubApi({
    ...RECORDS,
    "GET /api/claims/CLM-1001": shown,
    "GET /api/claims/CLM-1001/steps": steps,
    ...more,
  });
  render(<ClaimPage claimId="CLM-1001" />);
  return fetchMock;
}

function step(kind: Step["kind"], text: string, id: number): Step {
  return { step_id: id, kind, text, created_at: "2026-10-24T09:00:00+00:00" };
}

it("shows the claim in full with its policy and history", async () => {
  show(claim({}));
  expect(
    await screen.findByRole("heading", { name: "CLM-1001" }),
  ).toBeDefined();
  expect(screen.getByText("Flight home canceled by the airline")).toBeDefined();
  expect(
    screen.getByText("My flight home from Rome was canceled."),
  ).toBeDefined();
  expect(screen.getByText("Airport hotel")).toBeDefined();
  expect(screen.getByText("Hotel receipt")).toBeDefined();
  expect(screen.getByText("Jun 18, 2026, Rome, Italy")).toBeDefined();
  expect(await screen.findByText("Premium")).toBeDefined();
  expect(screen.getByText("Electronics plus")).toBeDefined();
  expect(screen.getByText("Jun 10, 2026 to Jun 18, 2026")).toBeDefined();
  expect(
    await screen.findByText("Checked bag arrived 30 hours late"),
  ).toBeDefined();
  expect(
    screen.getByText("No decision yet. Run the agent to decide this claim."),
  ).toBeDefined();
  expect(
    screen.getByText("The agent has not worked on this claim yet."),
  ).toBeDefined();
});

it("starts the agent on a waiting claim", async () => {
  const fetchMock = show(claim({}), [], {
    "POST /api/claims/CLM-1001/agent-runs": { thread_id: "t-1" },
  });
  const button = await screen.findByRole("button", { name: "Run the agent" });
  fireEvent.click(button);
  expect(button.hasAttribute("disabled")).toBe(true);
  expect(fetchMock).toHaveBeenCalledWith(
    "/api/claims/CLM-1001/agent-runs",
    expect.objectContaining({ method: "POST" }),
  );
});

it("says why the agent could not start", async () => {
  show(claim({}), [], {
    "POST /api/claims/CLM-1001/agent-runs": Response.json(
      { detail: "Claim CLM-1001 is in progress" },
      { status: 409 },
    ),
  });
  fireEvent.click(await screen.findByRole("button", { name: "Run the agent" }));
  expect((await screen.findByRole("alert")).textContent).toBe(
    "Claim CLM-1001 is in progress",
  );
});

it("shows the agent's steps while it works", async () => {
  show(claim({ status: "in_progress" }), [
    step("tool_call", "get_claim({})", 1),
    step("tool_result", 'get_claim: {"claim_id": "CLM-1001"}', 2),
    step("reply", "Approved and paid $420.00.", 3),
    step("error", "The run failed: timeout", 4),
  ]);
  expect(await screen.findByText("get_claim({})")).toBeDefined();
  expect(screen.getByText("get_claim")).toBeDefined();
  expect(screen.getByText('{"claim_id": "CLM-1001"}')).toBeDefined();
  expect(screen.getByText("Approved and paid $420.00.")).toBeDefined();
  expect(screen.getByText("Stopped")).toBeDefined();
  expect(
    screen.getAllByText("The agent is working on this claim."),
  ).toHaveLength(2);
  expect(screen.queryByRole("button", { name: "Run the agent" })).toBeNull();
});

it("shows a paid approval with its reasons", async () => {
  const payment = {
    amount: 420,
    paid_at: "2026-10-24T09:00:01+00:00",
    signed_off_by: null,
  };
  show(claim({ status: "decided", decision: { ...APPROVAL, payment } }));
  expect(
    await screen.findByRole("heading", { name: "Approved" }),
  ).toBeDefined();
  expect(
    screen.getByText("The delay is covered and the receipts support it."),
  ).toBeDefined();
  expect(
    screen.getByText("Policy wording: Section 3, Trip Delay"),
  ).toBeDefined();
  expect(screen.getByText(/^Paid/).textContent).toBe("Paid $420.00");
});

it("shows an approval that is not paid yet", async () => {
  show(claim({ status: "decided", decision: APPROVAL }));
  expect(await screen.findByText("Not paid yet.")).toBeDefined();
});

it("shows a decline without a payment", async () => {
  const decline = { ...APPROVAL, outcome: "decline" as const, payout: 0 };
  show(claim({ status: "decided", decision: decline }));
  expect(
    await screen.findByRole("heading", { name: "Declined" }),
  ).toBeDefined();
  expect(screen.queryByText(/Paid|Not paid/)).toBeNull();
});

it("lets a handler sign off a payout over the limit", async () => {
  const large = { ...APPROVAL, payout: 1150 };
  const fetchMock = show(
    claim({ status: "waiting_for_sign_off", decision: large }),
    [],
    {
      "POST /api/claims/CLM-1001/sign-off": claim({ status: "decided" }),
    },
  );
  expect(
    await screen.findByText("The payment waits for a handler's sign-off."),
  ).toBeDefined();
  const button = screen.getByRole("button", { name: "Sign off and pay" });
  expect(button.hasAttribute("disabled")).toBe(true);
  await screen.findByRole("option", { name: "Dana Whitfield" });
  fireEvent.change(screen.getByLabelText("Handler"), {
    target: { value: "HND-01" },
  });
  fireEvent.click(button);
  expect(fetchMock).toHaveBeenCalledWith(
    "/api/claims/CLM-1001/sign-off",
    expect.objectContaining({ body: JSON.stringify({ handler_id: "HND-01" }) }),
  );
});

it("says why a sign-off failed", async () => {
  const large = { ...APPROVAL, payout: 1150 };
  show(claim({ status: "waiting_for_sign_off", decision: large }), [], {
    "POST /api/claims/CLM-1001/sign-off": Response.json(
      { detail: "Handler HND-01 cannot sign off" },
      { status: 403 },
    ),
  });
  await screen.findByRole("option", { name: "Dana Whitfield" });
  fireEvent.change(screen.getByLabelText("Handler"), {
    target: { value: "HND-01" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Sign off and pay" }));
  expect((await screen.findByRole("alert")).textContent).toBe(
    "Handler HND-01 cannot sign off",
  );
});

it("shows a signed-off payment", async () => {
  const payment = {
    amount: 1150,
    paid_at: "2026-10-24T09:00:01+00:00",
    signed_off_by: "Dana Whitfield",
  };
  show(
    claim({
      status: "decided",
      decision: { ...APPROVAL, payout: 1150, payment },
    }),
  );
  expect((await screen.findByText(/^Paid/)).textContent).toBe(
    "Paid $1,150.00, signed off by Dana Whitfield",
  );
});

it("says when the claim cannot be loaded", async () => {
  stubApi({});
  render(<ClaimPage claimId="CLM-9999" />);
  expect((await screen.findByRole("alert")).textContent).toContain(
    "Claim CLM-9999 could not be loaded",
  );
});
