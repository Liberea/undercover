"""Run the UnderCover Agent: `uv run -m agent` works the whole queue,
`uv run -m agent --cap 5` works at most five claims, and
`uv run -m agent CLM-1001` works one claim."""

import argparse
import sys
import uuid

from agent.claim import run
from agent.queue import waiting_claims, work_queue


def main(argv: list[str]) -> None:
    """Work one named claim, or the queue up to the cap, printing each report."""
    parser = argparse.ArgumentParser(prog="uv run -m agent")
    parser.add_argument("claim_id", nargs="?", help="work this one claim")
    parser.add_argument("--cap", type=int, help="work at most this many claims")
    args = parser.parse_args(argv)
    if args.claim_id:
        print(run(args.claim_id, uuid.uuid4().hex), flush=True)
        return
    cap = args.cap or len(waiting_claims())
    if cap == 0:
        print("No claims are waiting.")
        return
    print(work_queue(uuid.uuid4().hex, cap), flush=True)


if __name__ == "__main__":
    main(sys.argv[1:])
