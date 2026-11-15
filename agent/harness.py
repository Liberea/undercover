"""The harness both agents run in: the model with retries and a limit on its
calls, the agent's own middleware and tools, and the stream of what it does."""

from collections.abc import Iterable, Iterator, Sequence
from dataclasses import dataclass
from typing import Any

from langchain.agents import create_agent
from langchain.agents.middleware import (
    AgentMiddleware,
    ModelCallLimitMiddleware,
    ModelRetryMiddleware,
)
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.tools import BaseTool

from agent.model import model

RETRY_DELAY_SECONDS = 1.0


@dataclass(frozen=True)
class Agent:
    """An agent to run: its instructions, its tools, how many model calls it may
    make, and any middleware of its own."""

    instructions: str
    tools: Sequence[BaseTool]
    call_limit: int
    middleware: Sequence[AgentMiddleware[Any, Any]] = ()


def retry() -> ModelRetryMiddleware:
    """Retry a failed model call twice, waiting longer each time, then raise."""
    return ModelRetryMiddleware(
        max_retries=2, initial_delay=RETRY_DELAY_SECONDS, on_failure="error"
    )


def messages(updates: Iterable[Any]) -> Iterator[AIMessage | ToolMessage]:
    """Yield each new message from the model and tools nodes' updates.

    The middleware's own nodes send updates too, but never messages.
    """
    for update in updates:
        for node in ("model", "tools"):
            if node in update:
                yield from update[node]["messages"]


def stream(
    agent: Agent, task: str, context: object, llm: BaseChatModel | None
) -> Iterator[AIMessage | ToolMessage]:
    """Run the agent on a task and yield each new message from the model and the
    tools. The tools and middleware read the context; the model never sees it."""
    graph = create_agent(
        llm or model(),
        tools=agent.tools,
        system_prompt=agent.instructions,
        middleware=[
            retry(),
            ModelCallLimitMiddleware(run_limit=agent.call_limit, exit_behavior="error"),
            *agent.middleware,
        ],
        context_schema=type(context),
    )
    updates = graph.stream(
        {"messages": [{"role": "user", "content": task}]},
        context=context,
        stream_mode="updates",
    )
    yield from messages(updates)
