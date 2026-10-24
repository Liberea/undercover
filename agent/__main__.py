"""Run the UnderCover Agent: `uv run -m agent CLM-1001` decides one claim, and
`uv run -m agent` works through every waiting claim in turn."""

import sys
import uuid

from agent.api import call
from agent.main import run


def waiting_claims() -> list[str]:
    """List the ids of the claims waiting in the queue."""
    claims = call("GET", "/api/claims", None)
    return [c["claim_id"] for c in claims if c["status"] == "waiting"]


def main(claim_ids: list[str]) -> None:
    """Run the agent on each claim and print its reply."""
    for claim_id in claim_ids or waiting_claims():
        print(f"{claim_id}: {run(claim_id, uuid.uuid4().hex)}", flush=True)


if __name__ == "__main__":
    main(sys.argv[1:])
