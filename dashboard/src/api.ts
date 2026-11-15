export type Status =
  | "waiting"
  | "in_progress"
  | "waiting_for_sign_off"
  | "decided"
  | "left_for_handler";
export type Outcome = "approve" | "decline" | "refer";
export type StepKind = "tool_call" | "tool_result" | "read" | "reply" | "error";

export interface ClaimSummary {
  claim_id: string;
  customer_name: string;
  claim_type: string;
  submitted_on: string;
  amount_claimed: number;
  status: Status;
  outcome: Outcome | null;
  payout: number | null;
}

export interface Item {
  description: string;
  category: string;
  amount: number;
}

export interface ClaimDocument {
  name: string;
  type: string;
  content: string;
}

export interface Payment {
  amount: number;
  paid_at: string;
  signed_off_by: string | null;
}

export interface Decision {
  outcome: Outcome;
  payout: number;
  reasons: string;
  policy_section: string;
  decided_at: string;
  payment: Payment | null;
}

export interface Claim {
  claim_id: string;
  policy_id: string;
  customer_id: string;
  customer_name: string;
  claim_type: string;
  submitted_on: string;
  incident_date: string;
  incident_location: string;
  summary: string;
  story: string;
  items: Item[];
  amount_claimed: number;
  documents: ClaimDocument[];
  status: Status;
  thread_id: string | null;
  decision: Decision | null;
}

export interface Policy {
  policy_id: string;
  plan: string;
  add_ons: string[];
  purchased_on: string;
  trip: {
    destination: string;
    departs_on: string;
    returns_on: string;
    trip_cost: number;
  };
  travelers: string[];
}

export interface PreviousClaim {
  claim_id: string;
  filed_on: string;
  claim_type: string;
  summary: string;
  outcome: string;
  amount_paid: number;
}

export interface ClaimHistory {
  name: string;
  customer_since: string;
  previous_claims: PreviousClaim[];
}

export interface Handler {
  handler_id: string;
  name: string;
  role: string;
}

export type TodoStatus = "to_do" | "in_progress" | "done" | "left_for_handler";

export interface Todo {
  content: string;
  status: TodoStatus;
}

export interface Run {
  run_id: string;
  cap: number;
  status: "running" | "finished";
  todos: Todo[];
  summary: string | null;
  started_at: string;
  finished_at: string | null;
}

export interface Step {
  step_id: number;
  kind: StepKind;
  text: string;
  created_at: string;
}

/** The message of a failed request, to show to the handler. */
export function message(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}

async function parse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const { detail } = (await response.json()) as { detail: string };
    throw new Error(detail);
  }
  return (await response.json()) as T;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  return parse<T>(await fetch(path, init));
}

function post<T>(path: string, body: unknown): Promise<T> {
  return request<T>(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export const listClaims = () => request<ClaimSummary[]>("/api/claims");
export const getClaim = (id: string) => request<Claim>(`/api/claims/${id}`);
export const getPolicy = (id: string) => request<Policy>(`/api/policies/${id}`);
export const getClaimHistory = (customerId: string) =>
  request<ClaimHistory>(`/api/customers/${customerId}/claims`);
export const listSteps = (id: string) =>
  request<Step[]>(`/api/claims/${id}/steps`);
export const listHandlers = () => request<Handler[]>("/api/handlers");
export const getInstructions = () =>
  request<{ queue: string; claim: string }>("/api/instructions");
export const runAgent = (id: string) =>
  post<{ thread_id: string }>(`/api/claims/${id}/agent-runs`, {});
export const signOff = (id: string, handlerId: string) =>
  post<Claim>(`/api/claims/${id}/sign-off`, { handler_id: handlerId });
export const runQueueAgent = (cap: number) =>
  post<{ run_id: string }>("/api/queue/agent-runs", { cap });

/** The queue agent's most recent run, or null before its first run. */
export async function getLatestRun(): Promise<Run | null> {
  const response = await fetch("/api/runs/latest");
  return response.status === 404 ? null : parse<Run>(response);
}
