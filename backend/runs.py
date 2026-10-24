"""The agent's runs on a claim and the steps it takes."""

import uuid

from fastapi import APIRouter, BackgroundTasks

from agent import main as agent
from backend.claims import find_claim
from backend.db import Db
from backend.lifecycle import now, require_status
from backend.models import AgentRun, Step, StepIn

router = APIRouter(prefix="/api/claims")


@router.post("/{claim_id}/steps", operation_id="add_step")
def add_step(claim_id: str, body: StepIn, db: Db) -> Step:
    """Record one step the agent took on a claim."""
    find_claim(db, claim_id)
    created_at = now()
    cursor = db.execute(
        "INSERT INTO steps (claim_id, thread_id, kind, text, created_at)"
        " VALUES (?, ?, ?, ?, ?)",
        (claim_id, body.thread_id, body.kind, body.text, created_at),
    )
    return Step(
        step_id=cursor.lastrowid or 0, created_at=created_at, **body.model_dump()
    )


@router.get("/{claim_id}/steps", operation_id="list_steps")
def list_steps(claim_id: str, db: Db) -> list[Step]:
    """List the steps the agent took on a claim, oldest first."""
    find_claim(db, claim_id)
    rows = db.execute(
        "SELECT step_id, thread_id, kind, text, created_at FROM steps"
        " WHERE claim_id = ? ORDER BY step_id",
        (claim_id,),
    ).fetchall()
    return [Step.model_validate(dict(row)) for row in rows]


@router.post("/{claim_id}/agent-runs", operation_id="run_agent", status_code=202)
def run_agent(claim_id: str, db: Db, background: BackgroundTasks) -> AgentRun:
    """Start the agent on a waiting claim; it works in the background."""
    require_status(find_claim(db, claim_id), "waiting")
    thread_id = uuid.uuid4().hex
    background.add_task(agent.run, claim_id, thread_id)
    return AgentRun(thread_id=thread_id)
