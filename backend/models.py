"""The shapes of the UnderCover API's requests and responses."""

from typing import Literal, Self

from pydantic import BaseModel, Field, model_validator

Status = Literal[
    "waiting", "in_progress", "waiting_for_sign_off", "decided", "left_for_handler"
]
Outcome = Literal["approve", "decline", "refer"]


class StartIn(BaseModel):
    thread_id: str


class DecisionIn(BaseModel):
    outcome: Outcome
    payout: float = Field(ge=0, description="0 unless the outcome is approve")
    reasons: str = Field(description="Two or three sentences")
    policy_section: str = Field(description="The policy wording section it rests on")

    @model_validator(mode="after")
    def only_approvals_pay(self) -> Self:
        """Reject a payout on a decline or a referral."""
        if self.outcome != "approve" and self.payout != 0:
            raise ValueError("Only an approval has a payout")
        return self


class PaymentIn(BaseModel):
    amount: float = Field(gt=0)


class SignOffIn(BaseModel):
    handler_id: str


StepKind = Literal["tool_call", "tool_result", "read", "reply", "error"]


class StepIn(BaseModel):
    thread_id: str
    kind: StepKind
    text: str


class Step(StepIn):
    step_id: int
    created_at: str


class AgentRun(BaseModel):
    thread_id: str


TodoStatus = Literal["to_do", "in_progress", "done", "left_for_handler"]


class Todo(BaseModel):
    content: str
    status: TodoStatus


class TodosIn(BaseModel):
    todos: list[Todo]


class CapIn(BaseModel):
    cap: int = Field(gt=0, description="The most claims the run may work")


class RunIn(CapIn):
    run_id: str


class FinishIn(BaseModel):
    summary: str


class Run(BaseModel):
    run_id: str
    cap: int
    status: Literal["running", "finished"]
    todos: list[Todo]
    summary: str | None
    started_at: str
    finished_at: str | None


class QueueAgentRun(BaseModel):
    run_id: str


class Instructions(BaseModel):
    queue: str
    claim: str


class Item(BaseModel):
    description: str
    category: str
    amount: float


class Document(BaseModel):
    name: str
    type: str
    content: str


class Payment(BaseModel):
    amount: float
    paid_at: str
    signed_off_by: str | None


class Decision(BaseModel):
    outcome: Outcome
    payout: float
    reasons: str
    policy_section: str
    decided_at: str
    payment: Payment | None


class ClaimSummary(BaseModel):
    claim_id: str
    customer_name: str
    claim_type: str
    submitted_on: str
    amount_claimed: float
    status: Status
    outcome: Outcome | None
    payout: float | None


class Claim(BaseModel):
    claim_id: str
    policy_id: str
    customer_id: str
    customer_name: str
    claim_type: str
    submitted_on: str
    incident_date: str
    incident_location: str
    summary: str
    story: str
    items: list[Item]
    amount_claimed: float
    documents: list[Document]
    status: Status
    thread_id: str | None
    decision: Decision | None


class Trip(BaseModel):
    destination: str
    departs_on: str
    returns_on: str
    trip_cost: float


class Policy(BaseModel):
    policy_id: str
    customer_id: str
    plan: str
    add_ons: list[str]
    purchased_on: str
    sold_through: str
    trip: Trip
    travelers: list[str]
    status: str


class PreviousClaim(BaseModel):
    claim_id: str
    filed_on: str
    incident_date: str
    claim_type: str
    summary: str
    outcome: str
    amount_paid: float


class ClaimHistory(BaseModel):
    customer_id: str
    name: str
    customer_since: str
    previous_claims: list[PreviousClaim]


class Handler(BaseModel):
    handler_id: str
    name: str
    role: str
    can_approve_over_limit: bool


class SectionHeading(BaseModel):
    section: int
    title: str
    topics: list[str]


class Section(BaseModel):
    document: str
    section: int
    title: str
    text: str
