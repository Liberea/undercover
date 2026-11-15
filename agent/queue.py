"""The queue agent: plans the run as a to-do list and hands each claim to a
claim agent, within the run's cap."""

import json
import threading
import uuid
from typing import Any, Literal, TypedDict

from langchain.agents import AgentState, create_agent
from langchain.agents.middleware import (
    AgentMiddleware,
    ModelCallLimitMiddleware,
    after_model,
)
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.tools import BaseTool, tool
from langgraph.runtime import Runtime

from agent import claim
from agent.api import call, request, tool_reply
from agent.model import model, retry
from agent.tools import path


class Todo(TypedDict):
    content: str
    status: Literal["to_do", "in_progress", "done", "left_for_handler"]


def waiting_claims() -> list[dict[str, Any]]:
    """List the claims waiting in the queue."""
    return [c for c in call("GET", "/api/claims", None) if c["status"] == "waiting"]


def model_call_limit(cap: int) -> int:
    """Allow a few model calls for each claim, and some to plan and sum up."""
    return 4 * cap + 10


def missed(taken: set[str], cap: int) -> list[str]:
    """Name the waiting claims the run should still work: its own claims that
    came back to the queue, and new ones while it is below its cap."""
    waiting = [c["claim_id"] for c in waiting_claims()]
    returned = [c for c in waiting if c in taken]
    new = [c for c in waiting if c not in taken][: cap - len(taken)]
    return returned + new


def check_for_missed_claims(taken: set[str], cap: int) -> AgentMiddleware:
    """Build the hook that sends the agent back when it finishes too early."""

    @after_model(can_jump_to=["model"])
    def check_for_missed_claims(
        state: AgentState, runtime: Runtime
    ) -> dict[str, Any] | None:
        """When the agent answers without a tool call, it wants to finish: send
        it back to the model if a waiting claim within its cap is missed."""
        last = state["messages"][-1]
        if isinstance(last, AIMessage) and last.tool_calls:
            return None
        names = missed(taken, cap)
        if not names:
            return None
        note = (
            "Before you finish: these waiting claims are within your cap and"
            f" not worked yet: {', '.join(names)}. Work them, then finish."
        )
        return {"messages": [HumanMessage(note)], "jump_to": "model"}

    return check_for_missed_claims


def tools_for_run(run_id: str, cap: int, taken: set[str]) -> list[BaseTool]:
    """Return the queue agent's tools, bound to this run and its cap."""
    lock = threading.Lock()

    @tool
    def list_claims() -> str:
        """List the claims waiting in the queue, with their id, type, amount
        claimed and the date they were submitted."""
        fields = ("claim_id", "claim_type", "amount_claimed", "submitted_on")
        return json.dumps([{f: c[f] for f in fields} for c in waiting_claims()])

    @tool
    def write_todos(todos: list[Todo]) -> str:
        """Replace your whole to-do list for this run, each item with its status."""
        response = request("PUT", path("runs", run_id, "todos"), {"todos": todos})
        return (
            "The to-do list is updated."
            if response.is_success
            else tool_reply(response)
        )

    @tool
    def work_claim(claim_id: str) -> str:
        """Hand one claim to a claim agent, which works it from a clean start and
        reports back in one line."""
        with lock:
            if claim_id not in taken:
                refusal = refuse_new_claim(claim_id, len(taken), cap)
                if refusal:
                    return refusal
                taken.add(claim_id)
            return claim.run(claim_id, uuid.uuid4().hex)

    return [list_claims, write_todos, work_claim]


def refuse_new_claim(claim_id: str, taken: int, cap: int) -> str | None:
    """Say why the run can't take on this claim, if it can't."""
    if taken >= cap:
        return (
            f"This run's cap of {cap} claims is reached, so {claim_id} stays waiting."
        )
    if claim_id not in {c["claim_id"] for c in waiting_claims()}:
        return f"{claim_id} is not waiting in the queue, so it was not started."
    return None


def work(run_id: str, cap: int, llm: BaseChatModel | None, instructions: str) -> str:
    """Stream the queue agent, print each claim's report and return the summary."""
    taken: set[str] = set()
    middleware: list[AgentMiddleware[Any, None]] = [
        retry(),
        ModelCallLimitMiddleware(
            run_limit=model_call_limit(cap), exit_behavior="error"
        ),
        check_for_missed_claims(taken, cap),
    ]
    agent = create_agent(
        llm or model(),
        tools=tools_for_run(run_id, cap, taken),
        system_prompt=instructions,
        middleware=middleware,
    )
    task = f"Work the waiting claims in the queue, up to {cap} claims."
    updates = agent.stream(
        {"messages": [{"role": "user", "content": task}]}, stream_mode="updates"
    )
    summary = ""
    for message in claim.messages(updates):
        if isinstance(message, ToolMessage) and message.name == "work_claim":
            print(message.text, flush=True)
        elif isinstance(message, AIMessage) and message.text.strip():
            summary = message.text
    return summary


def work_queue(run_id: str, cap: int, llm: BaseChatModel | None = None) -> str:
    """Work up to cap waiting claims in one run and return its summary.

    If the queue agent itself fails, the run is finished with the error.
    """
    call("POST", "/api/runs", {"run_id": run_id, "cap": cap})
    instructions = call("GET", "/api/instructions", None)["queue"]
    finish = path("runs", run_id, "finish")
    try:
        summary = work(run_id, cap, llm, instructions)
    except Exception as error:
        call("POST", finish, {"summary": f"The run stopped: {error}"})
        raise
    call("POST", finish, {"summary": summary})
    return summary
