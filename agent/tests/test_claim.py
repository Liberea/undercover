import pytest

from agent import claim as agent
from agent.tests.stubs import FlakyModel, broken, call, decide, reply, stub


def steps(client, claim_id):
    return client.get(f"/api/claims/{claim_id}/steps").json()


def status(client, claim_id):
    return client.get(f"/api/claims/{claim_id}").json()["status"]


def test_approve_under_the_limit_and_pay(client):
    model = stub(
        call("get_claim"),
        call("get_policy"),
        call("get_claim_history"),
        call("list_sections", document="claims_manual"),
        call("read_section", document="claims_manual", section=7),
        decide("approve", 420),
        call("pay_claim", amount=420),
        reply("Approved and paid $420.00."),
    )
    assert agent.run("CLM-1001", "t-1", model) == "CLM-1001: approved $420.00, paid"
    claim = client.get("/api/claims/CLM-1001").json()
    assert claim["status"] == "decided"
    assert claim["thread_id"] == "t-1"
    assert claim["decision"]["payment"]["amount"] == 420
    taken = steps(client, "CLM-1001")
    assert [s["kind"] for s in taken] == (
        ["tool_call", "tool_result"] * 4
        + ["tool_call", "read"]
        + ["tool_call", "tool_result"] * 2
        + ["reply"]
    )
    assert taken[0]["text"] == "get_claim({})"
    assert taken[1]["text"].startswith('get_claim: {"claim_id":"CLM-1001"')
    assert taken[9]["text"].startswith(
        "Claims manual, 7. Interpretation notes\n\nThese notes record"
    )
    assert taken[-1]["text"] == "Approved and paid $420.00."
    assert {s["thread_id"] for s in taken} == {"t-1"}


def test_payment_over_the_limit_is_held_even_if_the_agent_pays(client):
    model = stub(
        decide("approve", 1150),
        call("pay_claim", amount=1150),
        reply("Approved; the payment waits for a sign-off."),
    )
    report = agent.run("CLM-1002", "t-2", model)
    assert report == "CLM-1002: approved $1,150.00, waiting for sign-off"
    claim = client.get("/api/claims/CLM-1002").json()
    assert claim["status"] == "waiting_for_sign_off"
    assert claim["decision"]["payment"] is None
    pay_result = steps(client, "CLM-1002")[-2]
    assert pay_result["kind"] == "tool_result"
    assert "needs a handler's sign-off" in pay_result["text"]


@pytest.mark.parametrize(
    ("outcome", "line"), [("decline", "declined"), ("refer", "referred")]
)
def test_decline_and_refer_reports(client, outcome, line):
    model = stub(decide(outcome, 0), reply("Done."))
    assert agent.run("CLM-1001", "t-1", model) == f"CLM-1001: {line}"


def test_an_approval_left_unpaid_says_so(client):
    model = stub(decide("approve", 420), reply("Approved."))
    assert agent.run("CLM-1001", "t-1", model) == "CLM-1001: approved $420.00, not paid"


def test_a_run_without_a_decision_counts_as_a_failure(client):
    model = stub(call("get_claim"), reply("I cannot decide this claim."))
    report = agent.run("CLM-1001", "t-3", model)
    assert report == "CLM-1001: failed (it ended without a decision), back in the queue"
    assert status(client, "CLM-1001") == "waiting"
    last = steps(client, "CLM-1001")[-1]
    assert (last["kind"], last["text"]) == (
        "error",
        "The run failed: it ended without a decision",
    )


def test_a_failing_model_goes_back_to_the_queue_then_to_a_handler(client):
    first = agent.run("CLM-1001", "t-4", broken())
    assert first == "CLM-1001: failed (The model is unavailable), back in the queue"
    assert status(client, "CLM-1001") == "waiting"
    last = steps(client, "CLM-1001")[-1]
    assert (last["kind"], last["text"]) == (
        "error",
        "The run failed: The model is unavailable",
    )
    second = agent.run("CLM-1001", "t-5", broken())
    assert second == (
        "CLM-1001: failed twice (The model is unavailable), left for a handler"
    )
    assert status(client, "CLM-1001") == "left_for_handler"


def test_a_model_that_fails_once_is_retried(client):
    model = FlakyModel(messages=iter([decide("decline", 0), reply("Declined.")]))
    assert agent.run("CLM-1001", "t-6", model) == "CLM-1001: declined"
    assert model.failed


def test_the_call_limit_stops_an_agent_going_in_circles(client):
    model = stub(*[call("get_claim") for _ in range(agent.MODEL_CALL_LIMIT + 5)])
    report = agent.run("CLM-1001", "t-7", model)
    assert report.startswith("CLM-1001: failed (Model call limits exceeded")
    assert report.endswith("back in the queue")
    tool_calls = [s for s in steps(client, "CLM-1001") if s["kind"] == "tool_call"]
    assert len(tool_calls) == agent.MODEL_CALL_LIMIT


def test_a_claim_that_is_not_waiting_is_not_started(client):
    client.post("/api/claims/CLM-1001/start", json={"thread_id": "t-0"})
    client.post(
        "/api/claims/CLM-1001/decision",
        json={
            "outcome": "decline",
            "payout": 0,
            "reasons": "Not covered.",
            "policy_section": "Section 9",
        },
    )
    report = agent.run("CLM-1001", "t-8", stub(decide("approve", 420)))
    assert report == "CLM-1001: not started (Claim CLM-1001 is decided)"
    claim = client.get("/api/claims/CLM-1001").json()
    assert claim["decision"]["outcome"] == "decline"
    assert claim["thread_id"] == "t-0"


def test_blank_text_beside_a_tool_call_is_not_a_reply():
    message = call("get_claim")
    message.content = "\n\n"
    assert agent.steps(message) == [("tool_call", "get_claim({})")]


def test_middleware_updates_hold_no_messages():
    updates = [
        {"ModelCallLimitMiddleware.before_model": None},
        {"model": {"messages": [reply("Done.")]}},
        {"ModelCallLimitMiddleware.after_model": {"run_model_call_count": 1}},
    ]
    assert [m.text for m in agent.messages(updates)] == ["Done."]


def test_a_refused_read_is_a_result_not_a_read(client):
    model = stub(
        call("read_section", document="claims_manual", section=99),
        reply("I cannot decide this claim."),
    )
    agent.run("CLM-1001", "t-9", model)
    taken = steps(client, "CLM-1001")
    assert "read" not in [s["kind"] for s in taken]
    assert taken[1]["text"] == (
        'read_section: {"detail":"Section 99 of claims_manual not found"}'
    )


def test_instructions_come_from_the_api(client, monkeypatch):
    seen = {}
    real_create_agent = agent.create_agent

    def spy(*args, **kwargs):
        seen.update(kwargs)
        return real_create_agent(*args, **kwargs)

    monkeypatch.setattr(agent, "create_agent", spy)
    agent.run("CLM-1001", "t-10", stub(reply("Done.")))
    assert seen["system_prompt"] == client.get("/api/instructions").json()["claim"]
