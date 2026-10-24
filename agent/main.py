"""The UnderCover Agent."""

import json
import os
from collections.abc import Iterable, Iterator
from typing import Any

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, ToolMessage
from langchain_openai import ChatOpenAI
from pydantic import SecretStr

from agent.api import call
from agent.tools import TOOLS

load_dotenv(override=True)

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_MODEL = "openai/gpt-6-luna"
NO_DECISION = "The run ended without a decision, so the claim is back in the queue."


def model() -> ChatOpenAI:
    """Return the model named in MODEL_NAME, or GPT-6 Luna by default."""
    name = os.getenv("MODEL_NAME")
    return ChatOpenAI(
        model=name or DEFAULT_MODEL,
        base_url=OPENROUTER_BASE_URL,
        api_key=SecretStr(os.environ["OPENROUTER_API_KEY"]),
        reasoning_effort=None if name else "low",
    )


def add_step(claim_id: str, thread_id: str, kind: str, text: str) -> None:
    """Record one step on the claim, for the dashboard to show."""
    body = {"thread_id": thread_id, "kind": kind, "text": text}
    call("POST", f"/api/claims/{claim_id}/steps", body)


def messages(updates: Iterable[Any]) -> Iterator[AIMessage | ToolMessage]:
    """Yield each new message from the model and tools nodes' updates."""
    for update in updates:
        for node in update.values():
            yield from node["messages"]


def steps(message: AIMessage | ToolMessage) -> list[tuple[str, str]]:
    """Describe a message as the steps it holds: tool calls, a result or a reply."""
    if isinstance(message, ToolMessage):
        return [("tool_result", f"{message.name}: {message.text}")]
    found = [
        ("tool_call", f"{c['name']}({json.dumps(c['args'])})")
        for c in message.tool_calls
    ]
    if message.text:
        found.append(("reply", message.text))
    return found


def work(
    claim_id: str, thread_id: str, llm: BaseChatModel | None, instructions: str
) -> str:
    """Stream the agent on the claim, recording each step, and return its reply."""
    agent = create_agent(llm or model(), tools=TOOLS, system_prompt=instructions)
    updates = agent.stream(
        {"messages": [{"role": "user", "content": f"Decide claim {claim_id}."}]},
        config={"configurable": {"thread_id": thread_id}},
        stream_mode="updates",
    )
    reply = ""
    for message in messages(updates):
        for kind, text in steps(message):
            add_step(claim_id, thread_id, kind, text)
            if kind == "reply":
                reply = text
    return reply


def release_if_undecided(claim_id: str) -> bool:
    """Put the claim back in the queue if the run left it in progress."""
    if call("GET", f"/api/claims/{claim_id}", None)["status"] != "in_progress":
        return False
    call("POST", f"/api/claims/{claim_id}/release", None)
    return True


def run(claim_id: str, thread_id: str, llm: BaseChatModel | None = None) -> str:
    """Run the agent on one claim and return its final reply."""
    instructions = call("GET", "/api/instructions", None)["text"]
    call("POST", f"/api/claims/{claim_id}/start", {"thread_id": thread_id})
    try:
        reply = work(claim_id, thread_id, llm, instructions)
    except Exception as error:
        add_step(claim_id, thread_id, "error", f"The run failed: {error}")
        release_if_undecided(claim_id)
        raise
    if release_if_undecided(claim_id):
        add_step(claim_id, thread_id, "error", NO_DECISION)
    return reply
