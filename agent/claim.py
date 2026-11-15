"""The claim agent: works one claim from a clean start and reports in one line."""

import json
from collections.abc import Iterable, Iterator
from typing import Any

from langchain.agents import create_agent
from langchain.agents.middleware import AgentMiddleware, ModelCallLimitMiddleware
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, ToolMessage

from agent.api import call, request
from agent.model import model, retry
from agent.tools import path, tools_for

MODEL_CALL_LIMIT = 25
NO_DECISION = "it ended without a decision"


def add_step(claim_id: str, thread_id: str, kind: str, text: str) -> None:
    """Record one step on the claim, for the dashboard to show."""
    body = {"thread_id": thread_id, "kind": kind, "text": text}
    call("POST", path("claims", claim_id, "steps"), body)


def messages(updates: Iterable[Any]) -> Iterator[AIMessage | ToolMessage]:
    """Yield each new message from the model and tools nodes' updates.

    The middleware's own nodes send updates too, but never messages.
    """
    for update in updates:
        for node in ("model", "tools"):
            if node in update:
                yield from update[node]["messages"]


def steps(message: AIMessage | ToolMessage) -> list[tuple[str, str]]:
    """Describe a message as the steps it holds: tool calls, a result, a section
    read or a reply. A section that was read carries its heading as an artifact."""
    if isinstance(message, ToolMessage):
        if message.name == "read_section" and message.artifact:
            return [("read", message.text)]
        return [("tool_result", f"{message.name}: {message.text}")]
    found = [
        ("tool_call", f"{c['name']}({json.dumps(c['args'])})")
        for c in message.tool_calls
    ]
    if message.text.strip():
        found.append(("reply", message.text))
    return found


def work(
    claim_id: str, thread_id: str, llm: BaseChatModel | None, instructions: str
) -> None:
    """Stream the agent on the claim, recording each step."""
    middleware: list[AgentMiddleware[Any, None]] = [
        retry(),
        ModelCallLimitMiddleware(run_limit=MODEL_CALL_LIMIT, exit_behavior="error"),
    ]
    agent = create_agent(
        llm or model(),
        tools=tools_for(claim_id),
        system_prompt=instructions,
        middleware=middleware,
    )
    updates = agent.stream(
        {"messages": [{"role": "user", "content": f"Decide claim {claim_id}."}]},
        config={"configurable": {"thread_id": thread_id}},
        stream_mode="updates",
    )
    for message in messages(updates):
        for kind, text in steps(message):
            add_step(claim_id, thread_id, kind, text)


def release(claim_id: str, thread_id: str, reason: str) -> str:
    """Record why the run failed and release the claim, which counts the failure."""
    add_step(claim_id, thread_id, "error", f"The run failed: {reason}")
    status = call("POST", path("claims", claim_id, "release"), None)["status"]
    if status == "left_for_handler":
        return f"{claim_id}: failed twice ({reason}), left for a handler"
    return f"{claim_id}: failed ({reason}), back in the queue"


def report(claim: dict[str, Any]) -> str:
    """Describe a decided claim in one line: the outcome and the payment."""
    decision = claim["decision"]
    claim_id = claim["claim_id"]
    if decision["outcome"] == "decline":
        return f"{claim_id}: declined"
    if decision["outcome"] == "refer":
        return f"{claim_id}: referred"
    approved = f"{claim_id}: approved ${decision['payout']:,.2f}"
    if claim["status"] == "waiting_for_sign_off":
        return f"{approved}, waiting for sign-off"
    return f"{approved}, {'paid' if decision['payment'] else 'not paid'}"


def run(claim_id: str, thread_id: str, llm: BaseChatModel | None = None) -> str:
    """Work one claim and report the outcome in one line.

    A failure of the run never escapes: it is recorded and the claim released.
    """
    instructions = call("GET", "/api/instructions", None)["text"]
    started = request(
        "POST", path("claims", claim_id, "start"), {"thread_id": thread_id}
    )
    if not started.is_success:
        return f"{claim_id}: not started ({started.json()['detail']})"
    try:
        work(claim_id, thread_id, llm, instructions)
    except Exception as error:
        return release(claim_id, thread_id, str(error))
    claim = call("GET", path("claims", claim_id), None)
    if claim["status"] == "in_progress":
        return release(claim_id, thread_id, NO_DECISION)
    return report(claim)
