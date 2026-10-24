import { vi } from "vitest";
import type { Claim, ClaimSummary, Decision } from "./api";

/**
 * Answer each "METHOD /path" with its JSON, or with the Response given, and
 * anything else with a 404.
 */
export function stubApi(routes: Record<string, unknown>) {
  const fetchMock = vi.fn((path: string, init?: RequestInit) => {
    const key = `${init?.method ?? "GET"} ${path}`;
    const answer = routes[key];
    if (answer instanceof Response) return Promise.resolve(answer);
    return Promise.resolve(
      key in routes
        ? Response.json(answer)
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

export const APPROVAL: Decision = {
  outcome: "approve",
  payout: 420,
  reasons: "The delay is covered and the receipts support it.",
  policy_section: "Section 3, Trip Delay",
  decided_at: "2026-10-24T09:00:00+00:00",
  payment: null,
};

export function claim(overrides: Partial<Claim>): Claim {
  return {
    claim_id: "CLM-1001",
    policy_id: "POL-2001",
    customer_id: "CUS-3001",
    customer_name: "Maya Patel",
    claim_type: "trip_delay",
    submitted_on: "2026-06-24",
    incident_date: "2026-06-18",
    incident_location: "Rome, Italy",
    summary: "Flight home canceled by the airline",
    story: "My flight home from Rome was canceled.",
    items: [
      { description: "Airport hotel", category: "accommodation", amount: 245 },
    ],
    amount_claimed: 245,
    documents: [
      {
        name: "Hotel receipt",
        type: "receipt",
        content: "Total paid: $245.00.",
      },
    ],
    status: "waiting",
    thread_id: null,
    decision: null,
    ...overrides,
  };
}

export const RECORDS = {
  "GET /api/policies/POL-2001": {
    policy_id: "POL-2001",
    plan: "premium",
    add_ons: ["electronics_plus"],
    purchased_on: "2026-04-22",
    trip: {
      destination: "Rome, Italy",
      departs_on: "2026-06-10",
      returns_on: "2026-06-18",
      trip_cost: 3100,
    },
    travelers: ["Maya Patel"],
  },
  "GET /api/customers/CUS-3001/claims": {
    name: "Maya Patel",
    customer_since: "2023-04-11",
    previous_claims: [
      {
        claim_id: "CLM-0412",
        filed_on: "2024-08-19",
        claim_type: "baggage_delay",
        summary: "Checked bag arrived 30 hours late",
        outcome: "approved",
        amount_paid: 140,
      },
    ],
  },
  "GET /api/handlers": [
    {
      handler_id: "HND-01",
      name: "Dana Whitfield",
      role: "Senior Claims Handler",
    },
    { handler_id: "HND-02", name: "Marcus Oyelaran", role: "Claims Handler" },
  ],
};
