import inspect

import httpx
import pytest

from agent import api


def test_ids_are_escaped_in_paths():
    assert api.path("claims", "CLM-1002/release?") == (
        "/api/claims/CLM-1002%2Frelease%3F"
    )


def test_a_refusal_stops_the_run(client):
    with pytest.raises(Exception, match="409 Conflict"):
        api.result(api.release_claim("CLM-1001"))


def test_a_refusal_goes_back_to_the_model(client):
    reply = api.tool_reply(api.pay_claim("CLM-1001", 420))
    assert reply == '{"detail":"Claim CLM-1001 has no approval to pay"}'


def test_server_error_stops_the_run():
    response = httpx.Response(500, request=httpx.Request("GET", "http://test"))
    with pytest.raises(httpx.HTTPStatusError):
        api.tool_reply(response)


def test_each_function_is_named_for_a_backend_operation(client):
    operation_ids = {
        operation["operationId"]
        for methods in client.get("/openapi.json").json()["paths"].values()
        for operation in methods.values()
    }
    functions = {
        name
        for name, value in vars(api).items()
        if inspect.isfunction(value) and value.__module__ == api.__name__
    }
    helpers = {"backend", "path", "request", "result", "tool_reply"}
    assert functions - helpers <= operation_ids
