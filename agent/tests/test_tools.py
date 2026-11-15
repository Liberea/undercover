from langchain.tools import ToolRuntime

from agent import tools

DECISION = {
    "outcome": "decline",
    "payout": 0,
    "reasons": "Not covered.",
    "policy_section": "Section 9",
}


def runtime(client, claim_id="CLM-1001"):
    """The runtime a claim agent's tools get, holding the claim as context."""
    claim = client.get(f"/api/claims/{claim_id}").json()
    context = tools.ClaimContext(claim_id, claim["policy_id"], claim["customer_id"])
    return ToolRuntime(
        state={},
        context=context,
        config={},
        stream_writer=print,
        tool_call_id="c-1",
        store=None,
    )


def test_tools_read_the_claims_own_records(client):
    args = {"runtime": runtime(client)}
    assert '"plan":"premium"' in tools.get_policy.invoke(args)
    assert '"customer_id":"CUS-3001"' in tools.get_claim_history.invoke(args)
    assert '"claim_id":"CLM-1001"' in tools.get_claim.invoke(args)


def test_the_models_tools():
    assert [t.name for t in tools.CLAIM_TOOLS] == [
        "get_claim",
        "get_policy",
        "get_claim_history",
        "list_sections",
        "read_section",
        "decide_claim",
        "pay_claim",
    ]
    assert [t.name for t in tools.QUEUE_TOOLS] == [
        "list_claims",
        "write_todos",
        "work_claim",
    ]


def test_the_model_passes_no_record_ids_but_the_claim_to_work():
    claim_inputs = {arg for t in tools.CLAIM_TOOLS for arg in t.args}
    assert claim_inputs == {*DECISION, "amount", "document", "section"}
    queue_inputs = {arg for t in tools.QUEUE_TOOLS for arg in t.args}
    assert queue_inputs == {"todos", "claim_id"}


def test_list_sections(client):
    contents = tools.list_sections.invoke({"document": "claims_manual"})
    assert '"title":"Repeat claims"' in contents


def test_read_section_gives_its_heading_as_artifact(client):
    message = tools.read_section.invoke(
        {
            "type": "tool_call",
            "id": "c-1",
            "name": "read_section",
            "args": {"document": "policy_wording", "section": 3},
        }
    )
    assert message.artifact == "Policy wording, 3. Trip Delay"
    assert message.content.startswith("Policy wording, 3. Trip Delay\n\nWe pay when")


def test_tool_hands_a_refusal_to_the_model(client):
    reply = tools.pay_claim.invoke({"amount": 420, "runtime": runtime(client)})
    assert reply == '{"detail":"Claim CLM-1001 has no approval to pay"}'


def test_claim_tools_act_only_on_the_runs_claim(client):
    client.post("/api/claims/CLM-1001/start", json={"thread_id": "t-1"})
    client.post("/api/claims/CLM-1002/start", json={"thread_id": "t-2"})
    tools.decide_claim.invoke(DECISION | {"runtime": runtime(client)})
    assert client.get("/api/claims/CLM-1001").json()["status"] == "decided"
    assert client.get("/api/claims/CLM-1002").json()["status"] == "in_progress"


def test_tool_names_match_operation_ids(client):
    operation_ids = {
        operation["operationId"]
        for methods in client.get("/openapi.json").json()["paths"].values()
        for operation in methods.values()
    }
    assert {t.name for t in tools.CLAIM_TOOLS} <= operation_ids
