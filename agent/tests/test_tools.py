import httpx
import pytest

from agent import api, tools

DECISION = {
    "outcome": "decline",
    "payout": 0,
    "reasons": "Not covered.",
    "policy_section": "Section 9",
}


def tool(name, claim_id="CLM-1001"):
    return next(t for t in tools.tools_for(claim_id) if t.name == name)


def test_tools_read_the_claims_own_records(client):
    assert '"plan":"premium"' in tool("get_policy").invoke({})
    assert '"customer_id":"CUS-3001"' in tool("get_claim_history").invoke({})
    assert '"claim_id":"CLM-1001"' in tool("get_claim").invoke({})


def test_the_model_passes_no_ids(client):
    model_inputs = {arg for t in tools.tools_for("CLM-1001") for arg in t.args}
    assert model_inputs == {*DECISION, "amount"}


def test_tool_hands_a_refusal_to_the_model(client):
    reply = tool("pay_claim").invoke({"amount": 420})
    assert reply == '{"detail":"Claim CLM-1001 has no approval to pay"}'


def test_claim_tools_act_only_on_the_runs_claim(client):
    client.post("/api/claims/CLM-1001/start", json={"thread_id": "t-1"})
    client.post("/api/claims/CLM-1002/start", json={"thread_id": "t-2"})
    tool("decide_claim").invoke(DECISION)
    assert client.get("/api/claims/CLM-1001").json()["status"] == "decided"
    assert client.get("/api/claims/CLM-1002").json()["status"] == "in_progress"


def test_ids_are_escaped_in_paths():
    assert tools.path("claims", "CLM-1002/release?") == (
        "/api/claims/CLM-1002%2Frelease%3F"
    )


def test_tool_names_match_operation_ids(client):
    operation_ids = {
        operation["operationId"]
        for methods in client.get("/openapi.json").json()["paths"].values()
        for operation in methods.values()
    }
    assert {t.name for t in tools.tools_for("CLM-1001")} <= operation_ids


def test_server_error_stops_the_run():
    response = httpx.Response(500, request=httpx.Request("GET", "http://test"))
    with pytest.raises(httpx.HTTPStatusError):
        api.tool_reply(response)
