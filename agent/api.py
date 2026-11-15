"""The agent's client for the UnderCover backend's API: one function for each
operation the agent uses, named for it, with every path in this module.

Each function returns the backend's response, and the caller says what a refusal
means: `result` stops the run, `tool_reply` hands it to the model.
"""

from typing import Any
from urllib.parse import quote

import httpx

BACKEND_URL = "http://localhost:8000"


def backend() -> httpx.Client:
    """Return a client for the UnderCover backend."""
    return httpx.Client(base_url=BACKEND_URL, timeout=30)


def path(*parts: str) -> str:
    """Build an API path, escaping each part so an id can't add segments or a query."""
    return "/api/" + "/".join(quote(part, safe="") for part in parts)


def request(method: str, url: str, body: object = None) -> httpx.Response:
    """Send one request to the backend."""
    with backend() as client:
        return client.request(method, url, json=body)


def result(response: httpx.Response) -> Any:
    """Read the result of an operation the agent's own code relies on; any
    refusal stops the run."""
    response.raise_for_status()
    return response.json()


def tool_reply(response: httpx.Response) -> str:
    """Hand the backend's reply to the model, refusals included, as text."""
    if response.is_server_error:
        response.raise_for_status()
    return response.text


def get_instructions() -> httpx.Response:
    return request("GET", path("instructions"))


def list_claims() -> httpx.Response:
    return request("GET", path("claims"))


def get_claim(claim_id: str) -> httpx.Response:
    return request("GET", path("claims", claim_id))


def get_policy(policy_id: str) -> httpx.Response:
    return request("GET", path("policies", policy_id))


def get_claim_history(customer_id: str) -> httpx.Response:
    return request("GET", path("customers", customer_id, "claims"))


def list_sections(document: str) -> httpx.Response:
    return request("GET", path("documents", document, "sections"))


def read_section(document: str, section: int) -> httpx.Response:
    return request("GET", path("documents", document, "sections", str(section)))


def start_claim(claim_id: str, thread_id: str) -> httpx.Response:
    return request("POST", path("claims", claim_id, "start"), {"thread_id": thread_id})


def release_claim(claim_id: str) -> httpx.Response:
    return request("POST", path("claims", claim_id, "release"))


def decide_claim(
    claim_id: str, outcome: str, payout: float, reasons: str, policy_section: str
) -> httpx.Response:
    body = {
        "outcome": outcome,
        "payout": payout,
        "reasons": reasons,
        "policy_section": policy_section,
    }
    return request("POST", path("claims", claim_id, "decision"), body)


def pay_claim(claim_id: str, amount: float) -> httpx.Response:
    return request("POST", path("claims", claim_id, "payment"), {"amount": amount})


def add_step(claim_id: str, thread_id: str, kind: str, text: str) -> httpx.Response:
    body = {"thread_id": thread_id, "kind": kind, "text": text}
    return request("POST", path("claims", claim_id, "steps"), body)


def create_run(run_id: str, cap: int) -> httpx.Response:
    return request("POST", path("runs"), {"run_id": run_id, "cap": cap})


def write_todos(run_id: str, todos: list[Any]) -> httpx.Response:
    return request("PUT", path("runs", run_id, "todos"), {"todos": todos})


def finish_run(run_id: str, summary: str) -> httpx.Response:
    return request("POST", path("runs", run_id, "finish"), {"summary": summary})
