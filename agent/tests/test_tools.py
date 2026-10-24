import httpx
import pytest

from agent import api, tools


def tool(name, claim_id="CLM-1001"):
    return next(t for t in tools.tools_for(claim_id) if t.name == name)


def test_tool_reads_through_the_api(client):
    reply = tool("get_policy").invoke({"policy_id": "POL-2001"})
    assert '"plan":"premium"' in reply


def test_tool_hands_a_refusal_to_the_model(client):
    reply = tool("get_claim", "CLM-9999").invoke({})
    assert reply == '{"detail":"Claim CLM-9999 not found"}'


def test_ids_cannot_add_a_query_or_segments(client):
    reply = tool("get_policy").invoke({"policy_id": "POL-2001?x=1"})
    assert reply == '{"detail":"Policy POL-2001?x=1 not found"}'


def test_claim_tools_act_only_on_the_runs_claim(client):
    client.post("/api/claims/CLM-1001/start", json={"thread_id": "t-1"})
    client.post("/api/claims/CLM-1002/start", json={"thread_id": "t-2"})
    decision = {
        "outcome": "decline",
        "payout": 0,
        "reasons": "Not covered.",
        "policy_section": "Section 9",
    }
    tool("decide_claim", "CLM-1001").invoke(decision)
    assert client.get("/api/claims/CLM-1001").json()["status"] == "decided"
    assert client.get("/api/claims/CLM-1002").json()["status"] == "in_progress"


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
