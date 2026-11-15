"""The queue agent: plans the run as a to-do list and hands each claim to a
claim agent, within the run's cap."""

import threading
import uuid
from dataclasses import dataclass, field
from typing import Any

from langchain.agents import AgentState
from langchain.agents.middleware import after_model
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.runtime import Runtime

from agent import api, claim, harness
from agent.api import result
from agent.tools import QUEUE_TOOLS


def waiting_claims() -> list[dict[str, Any]]:
    """List the claims waiting in the queue."""
    return [c for c in result(api.list_claims()) if c["status"] == "waiting"]


def model_call_limit(cap: int) -> int:
    """Allow a few model calls for each claim the run can work, and some to plan
    and sum up. A cap above the waiting claims raises no limit."""
    return 4 * min(cap, len(waiting_claims())) + 10


@dataclass
class Run:
    """One run of the queue agent: its cap and the claims it has taken on. The
    agent's tools and middleware read it as their context."""

    run_id: str
    cap: int
    taken: set[str] = field(default_factory=set)
    lock: threading.Lock = field(default_factory=threading.Lock)

    def work_claim(self, claim_id: str) -> str:
        """Hand a claim to a claim agent and return its report. Claims asked for
        at once are worked one at a time, and a new claim beyond the cap, or one
        that is not waiting, is refused."""
        with self.lock:
            if claim_id not in self.taken:
                refusal = self.refusal(claim_id)
                if refusal:
                    return refusal
                self.taken.add(claim_id)
            return claim.run(claim_id, uuid.uuid4().hex)

    def refusal(self, claim_id: str) -> str | None:
        """Say why the run can't take on this claim, if it can't."""
        if len(self.taken) >= self.cap:
            return (
                f"This run's cap of {self.cap} claims is reached,"
                f" so {claim_id} stays waiting."
            )
        if claim_id not in {c["claim_id"] for c in waiting_claims()}:
            return f"{claim_id} is not waiting in the queue, so it was not started."
        return None

    def missed(self) -> list[str]:
        """Name the waiting claims the run should still work: its own claims that
        came back to the queue, and new ones while it is below its cap."""
        waiting = [c["claim_id"] for c in waiting_claims()]
        returned = [c for c in waiting if c in self.taken]
        new = [c for c in waiting if c not in self.taken]
        return returned + new[: self.cap - len(self.taken)]


@after_model(can_jump_to=["model"])
def check_for_missed_claims(
    state: AgentState, runtime: Runtime[Run]
) -> dict[str, Any] | None:
    """When the agent answers without a tool call, it wants to finish: send it
    back to the model if a waiting claim within its cap is missed."""
    last = state["messages"][-1]
    if isinstance(last, AIMessage) and last.tool_calls:
        return None
    names = runtime.context.missed()
    if not names:
        return None
    note = (
        "Before you finish: these waiting claims are within your cap and"
        f" not worked yet: {', '.join(names)}. Work them, then finish."
    )
    return {"messages": [HumanMessage(note)], "jump_to": "model"}


def work(run: Run, llm: BaseChatModel | None, instructions: str) -> str:
    """Stream the queue agent, print each claim's report and return the summary."""
    agent = harness.Agent(
        instructions,
        QUEUE_TOOLS,
        model_call_limit(run.cap),
        [check_for_missed_claims],
    )
    task = f"Work the waiting claims in the queue, up to {run.cap} claims."
    summary = ""
    for message in harness.stream(agent, task, run, llm):
        if isinstance(message, ToolMessage) and message.name == "work_claim":
            print(message.text, flush=True)
        elif isinstance(message, AIMessage) and message.text.strip():
            summary = message.text
    return summary


def work_queue(run_id: str, cap: int, llm: BaseChatModel | None = None) -> str:
    """Work up to cap waiting claims in one run and return its summary.

    If the queue agent itself fails, the run is finished with the error.
    """
    result(api.create_run(run_id, cap))
    instructions = result(api.get_instructions())["queue"]
    try:
        summary = work(Run(run_id, cap), llm, instructions)
    except Exception as error:
        result(api.finish_run(run_id, f"The run stopped: {error}"))
        raise
    result(api.finish_run(run_id, summary))
    return summary
