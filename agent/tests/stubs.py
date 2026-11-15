"""Stub models that give scripted replies in place of a real model."""

from itertools import count

from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage, BaseMessage
from pydantic import Field

ids = count()


class StubModel(GenericFakeChatModel):
    """A chat model that gives scripted replies in place of a real model, and
    keeps the last message it was given on each call."""

    seen: list[BaseMessage] = Field(default_factory=list)

    def bind_tools(self, tools, **kwargs):
        return self

    def _generate(self, messages, *args, **kwargs):
        self.seen.append(messages[-1])
        return super()._generate(messages, *args, **kwargs)


class BrokenModel(StubModel):
    """A chat model that fails the way an unavailable model does."""

    def _generate(self, *args, **kwargs):
        raise RuntimeError("The model is unavailable")


class FlakyModel(StubModel):
    """A chat model that fails on its first call, then gives its replies."""

    failed: bool = False

    def _generate(self, *args, **kwargs):
        if not self.failed:
            self.failed = True
            raise RuntimeError("The provider returned 502")
        return super()._generate(*args, **kwargs)


def stub(*replies):
    return StubModel(messages=iter(replies))


def broken():
    return BrokenModel(messages=iter([]))


def call(name, **args):
    return AIMessage(
        content="", tool_calls=[{"name": name, "args": args, "id": f"call-{next(ids)}"}]
    )


def decide(outcome, payout):
    return call(
        "decide_claim",
        outcome=outcome,
        payout=payout,
        reasons="The delay is covered.",
        policy_section="Section 3, Trip Delay",
    )


def reply(text):
    return AIMessage(content=text)
