import { cleanup, render, screen, within } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { Queue } from "./Queue";
import { stubApi, summary } from "./testing";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

const CLAIMS = [
  summary({}),
  summary({
    claim_id: "CLM-1002",
    customer_name: "Tomás Reyes",
    status: "waiting_for_sign_off",
    outcome: "approve",
    payout: 1150,
  }),
  summary({
    claim_id: "CLM-1003",
    claim_type: "emergency_medical",
    status: "decided",
    outcome: "decline",
    payout: 0,
  }),
];

it("lists each claim with its status and decision", async () => {
  stubApi({ "GET /api/claims": CLAIMS });
  render(<Queue />);
  expect(await screen.findByText("3 claims")).toBeDefined();
  const first = screen.getByRole("row", { name: /CLM-1001/ });
  expect(within(first).getByText("Trip delay")).toBeDefined();
  expect(within(first).getByText("Jun 24, 2026")).toBeDefined();
  expect(within(first).getByText("$420.00")).toBeDefined();
  expect(within(first).getByText("Waiting")).toBeDefined();
  const second = screen.getByRole("row", { name: /CLM-1002/ });
  expect(within(second).getByText("Waiting for sign-off")).toBeDefined();
  expect(within(second).getByText("$1,150.00")).toBeDefined();
  const third = screen.getByRole("row", { name: /CLM-1003/ });
  expect(within(third).getByText("Declined")).toBeDefined();
  expect(within(third).getByText("Emergency medical")).toBeDefined();
});

it("counts the claims in each state", async () => {
  stubApi({ "GET /api/claims": CLAIMS });
  render(<Queue />);
  const legend = await screen.findByRole("list", {
    name: "Where the claims stand",
  });
  const items = within(legend).getAllByRole("listitem");
  expect(items.map((item) => item.textContent)).toEqual([
    "1 Waiting",
    "0 In progress",
    "1 Waiting for sign-off",
    "1 Decided",
  ]);
});

it("links each claim to its page", async () => {
  stubApi({ "GET /api/claims": CLAIMS });
  render(<Queue />);
  const link = await screen.findByRole("link", { name: "CLM-1002" });
  expect(link.getAttribute("href")).toBe("#/claims/CLM-1002");
});

it("says when the backend is not responding", async () => {
  vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("offline")));
  render(<Queue />);
  expect((await screen.findByRole("alert")).textContent).toContain(
    "Start it with npm run dev",
  );
});
