import { vi } from "vitest";
import type { ClaimSummary } from "./api";

/** Answer each "METHOD /path" with its JSON, and anything else with a 404. */
export function stubApi(routes: Record<string, unknown>) {
  const fetchMock = vi.fn((path: string, init?: RequestInit) => {
    const key = `${init?.method ?? "GET"} ${path}`;
    return Promise.resolve(
      key in routes
        ? Response.json(routes[key])
        : Response.json({ detail: `No stub for ${key}` }, { status: 404 }),
    );
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

export function summary(overrides: Partial<ClaimSummary>): ClaimSummary {
  return {
    claim_id: "CLM-1001",
    customer_name: "Maya Patel",
    claim_type: "trip_delay",
    submitted_on: "2026-06-24",
    amount_claimed: 420,
    status: "waiting",
    outcome: null,
    payout: null,
    ...overrides,
  };
}
