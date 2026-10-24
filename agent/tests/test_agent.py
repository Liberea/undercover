from itertools import count

import pytest
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage

from agent import main

ids = count()


class StubModel(GenericFakeChatModel):
    """A chat model that gives scripted replies in place of a real model."""

    def bind_tools(self, tools, **kwargs):
        return self


class BrokenModel(StubModel):
    """A chat model that fails the way an unavailable model does."""

    def _generate(self, *args, **kwargs):
        raise RuntimeError("The model is unavailable")


def stub(*replies):
    return StubModel(messages=iter(replies))


def call(name, **args):
    return AIMessage(
        content="", tool_calls=[{"name": name, "args": args, "id": f"call-{next(ids)}"}]
    )


def decide(claim_id, outcome, payout):
    return call(
        "decide_claim",
        claim_id=claim_id,
        outcome=outcome,
        payout=payout,
        reasons="The delay is covered.",
        policy_section="Section 3, Trip Delay",
    )


def steps(client, claim_id):
    return client.get(f"/api/claims/{claim_id}/steps").json()


def test_approve_under_the_limit_and_pay(client):
    model = stub(
        call("get_claim", claim_id="CLM-1001"),
        call("get_policy", policy_id="POL-2001"),
        call("get_claim_history", customer_id="CUS-3001"),
        call("get_policy_wording"),
        decide("CLM-1001", "approve", 420),
        call("pay_claim", claim_id="CLM-1001", amount=420),
        AIMessage(content="Approved and paid $420.00."),
    )
    assert main.run("CLM-1001", "t-1", model) == "Approved and paid $420.00."
    claim = client.get("/api/claims/CLM-1001").json()
    assert claim["status"] == "decided"
    assert claim["thread_id"] == "t-1"
    assert claim["decision"]["payment"]["amount"] == 420
    taken = steps(client, "CLM-1001")
    assert [s["kind"] for s in taken] == ["tool_call", "tool_result"] * 6 + ["reply"]
    assert taken[0]["text"] == 'get_claim({"claim_id": "CLM-1001"})'
    assert taken[1]["text"].startswith('get_claim: {"claim_id":"CLM-1001"')
    assert taken[-1]["text"] == "Approved and paid $420.00."
    assert {s["thread_id"] for s in taken} == {"t-1"}


def test_payment_over_the_limit_is_held_even_if_the_agent_pays(client):
    model = stub(
        call("get_claim", claim_id="CLM-1002"),
        decide("CLM-1002", "approve", 1150),
        call("pay_claim", claim_id="CLM-1002", amount=1150),
        AIMessage(content="Approved; the payment waits for a sign-off."),
    )
    main.run("CLM-1002", "t-2", model)
    claim = client.get("/api/claims/CLM-1002").json()
    assert claim["status"] == "waiting_for_sign_off"
    assert claim["decision"]["payment"] is None
    pay_result = steps(client, "CLM-1002")[-2]
    assert pay_result["kind"] == "tool_result"
    assert "needs a handler's sign-off" in pay_result["text"]


def test_run_without_a_decision_goes_back_to_the_queue(client):
    model = stub(
        call("get_claim", claim_id="CLM-1001"),
        AIMessage(content="I cannot decide this claim."),
    )
    main.run("CLM-1001", "t-3", model)
    assert client.get("/api/claims/CLM-1001").json()["status"] == "waiting"
    last = steps(client, "CLM-1001")[-1]
    assert (last["kind"], last["text"]) == ("error", main.NO_DECISION)


def test_failed_run_goes_back_to_the_queue(client):
    with pytest.raises(RuntimeError, match="The model is unavailable"):
        main.run("CLM-1001", "t-4", BrokenModel(messages=iter([])))
    assert client.get("/api/claims/CLM-1001").json()["status"] == "waiting"
    last = steps(client, "CLM-1001")[-1]
    assert (last["kind"], last["text"]) == (
        "error",
        "The run failed: The model is unavailable",
    )


def test_instructions_come_from_the_api(client, monkeypatch):
    seen = {}
    real_create_agent = main.create_agent

    def spy(*args, **kwargs):
        seen.update(kwargs)
        return real_create_agent(*args, **kwargs)

    monkeypatch.setattr(main, "create_agent", spy)
    main.run("CLM-1001", "t-5", stub(AIMessage(content="Done.")))
    assert seen["system_prompt"] == client.get("/api/instructions").json()["text"]


def test_model_name(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.delenv("MODEL_NAME", raising=False)
    assert main.model().model_name == "openai/gpt-6-luna"
    monkeypatch.setenv("MODEL_NAME", "openrouter/free")
    assert main.model().model_name == "openrouter/free"
