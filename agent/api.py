"""The agent's client for the UnderCover backend's API."""

from typing import Any

import httpx

BACKEND_URL = "http://localhost:8000"


def backend() -> httpx.Client:
    """Return a client for the UnderCover backend."""
    return httpx.Client(base_url=BACKEND_URL, timeout=30)


def request(method: str, path: str, body: object) -> httpx.Response:
    """Send one request to the backend."""
    with backend() as client:
        return client.request(method, path, json=body)


def call(method: str, path: str, body: object) -> Any:
    """Call an operation the agent's own code relies on; any refusal stops the run."""
    response = request(method, path, body)
    response.raise_for_status()
    return response.json()


def tool_reply(response: httpx.Response) -> str:
    """Hand the backend's reply to the model, refusals included, as text."""
    if response.is_server_error:
        response.raise_for_status()
    return response.text
