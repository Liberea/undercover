from itertools import count

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from agent import api, harness, queue, tools
from agent.tests.stubs import broken, call, decide, reply, stub


def todo(content, status):
    return {"content": content, "status": status}


def declines():
    """A claim agent's model that declines the claim it is given."""
    return stub(decide("decline", 0), reply("Declined."))


@pytest.fixture
def claim_models(monkeypatch):
    """Give each claim agent the next of the models listed, and count them."""
    used = count()

    def give(*models):
        listed = iter(models)

        def next_model():
            next(used)
            return next(listed)

        monkeypatch.setattr(harness, "model", next_model)
        return used

    return give


def status(client, claim_id):
    return client.get(f"/api/claims/{claim_id}").json()["status"]


def latest_run(client):
    return client.get("/api/runs/latest").json()


def nudges(model):
    return [m.text for m in model.seen if isinstance(m, HumanMessage)][1:]


def test_the_to_do_list_is_stored(client, claim_models, monkeypatch):
    claim_models(declines())
    versions = []
    real_write_todos = api.write_todos

    def watch(*args):
        response = real_write_todos(*args)
        versions.append(latest_run(client)["todos"])
        return response

    monkeypatch.setattr(api, "write_todos", watch)
    planned = [todo("Work CLM-1001", "to_do"), todo("Write the summary", "to_do")]
    finished = [todo("Work CLM-1001", "done"), todo("Write the summary", "done")]
    model = stub(
        call("list_claims"),
        call("write_todos", todos=planned),
        call("work_claim", claim_id="CLM-1001"),
        call("write_todos", todos=finished),
        reply("Declined CLM-1001."),
    )
    assert queue.work_queue("r-1", 1, model) == "Declined CLM-1001."
    assert versions == [planned, finished]
    run = latest_run(client)
    assert run["status"] == "finished"
    assert run["summary"] == "Declined CLM-1001."
    assert run["todos"] == finished
    assert status(client, "CLM-1001") == "decided"


def test_the_cap_leaves_the_other_claims_waiting(client, claim_models, capsys):
    used = claim_models(declines(), declines())
    model = stub(
        call("work_claim", claim_id="CLM-1001"),
        call("work_claim", claim_id="CLM-1002"),
        call("work_claim", claim_id="CLM-1003"),
        reply("Worked two claims."),
    )
    queue.work_queue("r-1", 2, model)
    assert capsys.readouterr().out.splitlines() == [
        "CLM-1001: declined",
        "CLM-1002: declined",
        "This run's cap of 2 claims is reached, so CLM-1003 stays waiting.",
    ]
    assert next(used) == 2
    statuses = [c["status"] for c in client.get("/api/claims").json()]
    assert statuses.count("waiting") == 23
    assert nudges(model) == []


def test_a_failed_claim_does_not_stop_the_run_and_is_tried_again(
    client, claim_models, capsys
):
    claim_models(broken(), declines(), declines())
    model = stub(
        call("work_claim", claim_id="CLM-1001"),
        call("work_claim", claim_id="CLM-1002"),
        reply("Done."),
        call("work_claim", claim_id="CLM-1001"),
        reply("Declined both claims."),
    )
    assert queue.work_queue("r-1", 2, model) == "Declined both claims."
    assert capsys.readouterr().out.splitlines() == [
        "CLM-1001: failed (The model is unavailable), back in the queue",
        "CLM-1002: declined",
        "CLM-1001: declined",
    ]
    assert status(client, "CLM-1001") == "decided"
    assert latest_run(client)["status"] == "finished"


def test_a_claim_that_fails_twice_is_left_for_a_handler(client, claim_models, capsys):
    used = claim_models(broken(), broken())
    model = stub(
        call("work_claim", claim_id="CLM-1001"),
        reply("Done."),
        call("work_claim", claim_id="CLM-1001"),
        reply("CLM-1001 is left for a handler."),
    )
    queue.work_queue("r-1", 1, model)
    assert capsys.readouterr().out.splitlines()[-1] == (
        "CLM-1001: failed twice (The model is unavailable), left for a handler"
    )
    assert status(client, "CLM-1001") == "left_for_handler"
    assert next(used) == 2
    assert latest_run(client)["summary"] == "CLM-1001 is left for a handler."


def test_the_check_for_missed_claims(client, claim_models):
    claim_models(declines(), declines())
    model = stub(
        call("work_claim", claim_id="CLM-1001"),
        reply("Done."),
        call("work_claim", claim_id="CLM-1002"),
        reply("Declined two claims."),
    )
    queue.work_queue("r-1", 2, model)
    assert nudges(model) == [
        "Before you finish: these waiting claims are within your cap and not"
        " worked yet: CLM-1002. Work them, then finish."
    ]
    assert status(client, "CLM-1002") == "decided"


def test_work_claim_refuses_a_claim_that_is_not_waiting(client, claim_models):
    claim_models(declines())
    run = queue.Run("r-1", 2)
    run.work_claim("CLM-1001")
    report = run.work_claim("CLM-1001")
    assert report == "CLM-1001: not started (Claim CLM-1001 is decided)"
    unknown = run.work_claim("CLM-9999")
    assert unknown == "CLM-9999 is not waiting in the queue, so it was not started."
    assert run.taken == {"CLM-1001"}
    decision = client.get("/api/claims/CLM-1001").json()["decision"]
    assert decision["outcome"] == "decline"


def test_claims_asked_for_at_once_are_worked_one_at_a_time(client, claim_models):
    claim_models(declines(), declines())
    both = AIMessage(
        content="",
        tool_calls=[
            {"name": "work_claim", "args": {"claim_id": cid}, "id": f"w-{cid}"}
            for cid in ("CLM-1001", "CLM-1002")
        ],
    )
    queue.work_queue("r-1", 1, stub(both, reply("Done.")))
    statuses = {status(client, c) for c in ("CLM-1001", "CLM-1002")}
    assert statuses == {"decided", "waiting"}


def test_list_claims_shows_only_the_waiting_claims(client):
    client.post("/api/claims/CLM-1001/start", json={"thread_id": "t-1"})
    listed = tools.list_claims.invoke({})
    assert '"claim_id": "CLM-1001"' not in listed
    assert '{"claim_id": "CLM-1002", "claim_type": "baggage"' in listed


def test_a_failed_queue_agent_finishes_the_run_with_the_error(client):
    with pytest.raises(RuntimeError, match="The model is unavailable"):
        queue.work_queue("r-1", 2, broken())
    run = latest_run(client)
    assert run["status"] == "finished"
    assert run["summary"] == "The run stopped: The model is unavailable"


def test_each_agent_gets_its_own_instructions(client, claim_models, monkeypatch):
    claim_models(declines())
    prompts = []
    real_create_agent = harness.create_agent

    def spy(*args, **kwargs):
        prompts.append(kwargs["system_prompt"])
        return real_create_agent(*args, **kwargs)

    monkeypatch.setattr(harness, "create_agent", spy)
    model = stub(call("work_claim", claim_id="CLM-1001"), reply("Done."))
    queue.work_queue("r-1", 1, model)
    instructions = client.get("/api/instructions").json()
    assert prompts == [instructions["queue"], instructions["claim"]]


def test_the_model_call_limit_grows_with_the_claims_the_run_can_work(client):
    assert queue.model_call_limit(5) == 30
    assert queue.model_call_limit(1_000_000) == 4 * 25 + 10
