"""The claim agent: works one claim from a clean start and reports in one line."""

import json
from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, ToolMessage

from agent import api, harness
from agent.api import result
from agent.tools import CLAIM_TOOLS, ClaimContext

MODEL_CALL_LIMIT = 25
NO_DECISION = "it ended without a decision"


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
    claim: ClaimContext, thread_id: str, llm: BaseChatModel | None, instructions: str
) -> None:
    """Stream the agent on the claim, recording each step."""
    agent = harness.Agent(instructions, CLAIM_TOOLS, MODEL_CALL_LIMIT)
    task = f"Decide claim {claim.claim_id}."
    for message in harness.stream(agent, task, claim, llm):
        for kind, text in steps(message):
            result(api.add_step(claim.claim_id, thread_id, kind, text))


def release(claim_id: str, thread_id: str, reason: str) -> str:
    """Record why the run failed and release the claim, which counts the failure."""
    result(api.add_step(claim_id, thread_id, "error", f"The run failed: {reason}"))
    status = result(api.release_claim(claim_id))["status"]
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
    instructions = result(api.get_instructions())["claim"]
    started = api.start_claim(claim_id, thread_id)
    if not started.is_success:
        return f"{claim_id}: not started ({started.json()['detail']})"
    claim = started.json()
    context = ClaimContext(claim_id, claim["policy_id"], claim["customer_id"])
    try:
        work(context, thread_id, llm, instructions)
    except Exception as error:
        return release(claim_id, thread_id, str(error))
    decided = result(api.get_claim(claim_id))
    if decided["status"] == "in_progress":
        return release(claim_id, thread_id, NO_DECISION)
    return report(decided)
