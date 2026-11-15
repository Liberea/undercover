"""The agents' tools. Each calls one API operation, except work_claim, which hands
a claim to a claim agent. The run's context, never the model, says which claim or
run a tool acts on, so nothing in a claim can steer it to another record."""

import json
from dataclasses import dataclass
from typing import Literal, Protocol, TypedDict, runtime_checkable

from langchain.tools import ToolRuntime, tool

from agent import api
from agent.api import result, tool_reply

Document = Literal["policy_wording", "claims_manual"]


@dataclass(frozen=True)
class ClaimContext:
    """The claim a claim agent works on, with its policy and its customer."""

    claim_id: str
    policy_id: str
    customer_id: str


@runtime_checkable
class QueueRun(Protocol):
    """The run a queue agent works on, as its tools see it. The queue's own rules,
    in agent/queue.py, decide whether a claim can be worked. A protocol, since
    agent/queue.py imports this module."""

    run_id: str

    def work_claim(self, claim_id: str) -> str: ...


class Todo(TypedDict):
    content: str
    status: Literal["to_do", "in_progress", "done", "left_for_handler"]


@tool
def get_claim(runtime: ToolRuntime[ClaimContext]) -> str:
    """Get the claim in full: the story, the items claimed and the documents."""
    return tool_reply(api.get_claim(runtime.context.claim_id))


@tool
def get_policy(runtime: ToolRuntime[ClaimContext]) -> str:
    """Get the claim's policy: the plan, the add-ons, the trip and the travelers."""
    return tool_reply(api.get_policy(runtime.context.policy_id))


@tool
def get_claim_history(runtime: ToolRuntime[ClaimContext]) -> str:
    """Get the customer's earlier claims."""
    return tool_reply(api.get_claim_history(runtime.context.customer_id))


@tool
def list_sections(document: Document) -> str:
    """List the numbered sections of the policy wording or the claims manual, with
    the topics in each."""
    return tool_reply(api.list_sections(document))


@tool(response_format="content_and_artifact")
def read_section(document: Document, section: int) -> tuple[str, str | None]:
    """Read one numbered section of the policy wording or the claims manual."""
    response = api.read_section(document, section)
    if not response.is_success:
        return tool_reply(response), None
    found = response.json()
    name = document.replace("_", " ").capitalize()
    heading = f"{name}, {section}. {found['title']}"
    return f"{heading}\n\n{found['text']}", heading


@tool
def decide_claim(
    outcome: Literal["approve", "decline", "refer"],
    payout: float,
    reasons: str,
    policy_section: str,
    runtime: ToolRuntime[ClaimContext],
) -> str:
    """Record the decision on the claim: the outcome, the payout in US dollars
    (0 unless you approve), two or three sentences of reasons, and the policy
    wording section it rests on."""
    claim_id = runtime.context.claim_id
    return tool_reply(
        api.decide_claim(claim_id, outcome, payout, reasons, policy_section)
    )


@tool
def pay_claim(amount: float, runtime: ToolRuntime[ClaimContext]) -> str:
    """Pay the approved claim exactly its payout in US dollars."""
    return tool_reply(api.pay_claim(runtime.context.claim_id, amount))


@tool
def list_claims() -> str:
    """List the claims waiting in the queue, with their id, type, amount
    claimed and the date they were submitted."""
    fields = ("claim_id", "claim_type", "amount_claimed", "submitted_on")
    waiting = [c for c in result(api.list_claims()) if c["status"] == "waiting"]
    return json.dumps([{f: c[f] for f in fields} for c in waiting])


@tool
def write_todos(todos: list[Todo], runtime: ToolRuntime[QueueRun]) -> str:
    """Replace your whole to-do list for this run, each item with its status."""
    response = api.write_todos(runtime.context.run_id, todos)
    return "The to-do list is updated." if response.is_success else tool_reply(response)


@tool
def work_claim(claim_id: str, runtime: ToolRuntime[QueueRun]) -> str:
    """Hand one claim to a claim agent, which works it from a clean start and
    reports back in one line."""
    return runtime.context.work_claim(claim_id)


CLAIM_TOOLS = [
    get_claim,
    get_policy,
    get_claim_history,
    list_sections,
    read_section,
    decide_claim,
    pay_claim,
]
QUEUE_TOOLS = [list_claims, write_todos, work_claim]
