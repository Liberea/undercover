"""The UnderCover Agent's instructions, and starting it in the background on a
claim or on the queue. The one module of the backend that imports the agent."""

import uuid
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks

from agent import claim, queue
from backend.claims import find_claim
from backend.db import Db
from backend.lifecycle import require_status
from backend.models import AgentRun, CapIn, Instructions, QueueAgentRun

router = APIRouter(prefix="/api")

INSTRUCTIONS = Path(__file__).parent / "instructions"


@router.get("/instructions", operation_id="get_instructions")
def get_instructions() -> Instructions:
    """Get the UnderCover Agent's instructions for the queue and for a claim."""
    return Instructions(
        queue=(INSTRUCTIONS / "queue.md").read_text(encoding="utf-8"),
        claim=(INSTRUCTIONS / "claim.md").read_text(encoding="utf-8"),
    )


@router.post("/claims/{claim_id}/agent-runs", operation_id="run_agent", status_code=202)
def run_agent(claim_id: str, db: Db, background: BackgroundTasks) -> AgentRun:
    """Start the agent on a waiting claim; it works in the background."""
    require_status(find_claim(db, claim_id), "waiting")
    thread_id = uuid.uuid4().hex
    background.add_task(claim.run, claim_id, thread_id)
    return AgentRun(thread_id=thread_id)


@router.post("/queue/agent-runs", operation_id="run_queue_agent", status_code=202)
def run_queue_agent(body: CapIn, background: BackgroundTasks) -> QueueAgentRun:
    """Start the queue agent on the waiting claims; it works in the background."""
    run_id = uuid.uuid4().hex
    background.add_task(queue.work_queue, run_id, body.cap)
    return QueueAgentRun(run_id=run_id)
