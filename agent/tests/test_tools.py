import httpx
import pytest

from agent import api, tools


def test_tool_reads_through_the_api(client):
    assert '"plan":"premium"' in tools.get_policy.invoke({"policy_id": "POL-2001"})


def test_tool_hands_a_refusal_to_the_model(client):
    reply = tools.get_claim.invoke({"claim_id": "CLM-9999"})
    assert reply == '{"detail":"Claim CLM-9999 not found"}'


def test_tool_names_match_operation_ids(client):
    operation_ids = {
        operation["operationId"]
        for methods in client.get("/openapi.json").json()["paths"].values()
        for operation in methods.values()
    }
    assert {t.name for t in tools.TOOLS} <= operation_ids


def test_server_error_stops_the_run():
    response = httpx.Response(500, request=httpx.Request("GET", "http://test"))
    with pytest.raises(httpx.HTTPStatusError):
        api.tool_reply(response)
