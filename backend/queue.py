"""The queue agent's runs: their cap, their to-do list and their summary."""

import json
import sqlite3
import uuid

from fastapi import APIRouter, BackgroundTasks, HTTPException

from agent import queue as agent
from backend.db import Db
from backend.lifecycle import now
from backend.models import CapIn, FinishIn, QueueAgentRun, Run, RunIn, TodosIn

router = APIRouter(prefix="/api")


def find_run(db: sqlite3.Connection, run_id: str) -> Run:
    """Return a run, or raise 404."""
    row = db.execute("SELECT * FROM runs WHERE run_id = ?", (run_id,)).fetchone()
    if row is None:
        raise HTTPException(404, f"Run {run_id} not found")
    return Run.model_validate(dict(row) | {"todos": json.loads(row["todos"])})


@router.post("/runs", operation_id="create_run", status_code=201)
def create_run(body: RunIn, db: Db) -> Run:
    """Record the start of a run of the queue agent, capped at a number of claims."""
    db.execute(
        "INSERT INTO runs (run_id, cap, status, todos, started_at)"
        " VALUES (?, ?, 'running', '[]', ?)",
        (body.run_id, body.cap, now()),
    )
    return find_run(db, body.run_id)


@router.put("/runs/{run_id}/todos", operation_id="write_todos")
def write_todos(run_id: str, body: TodosIn, db: Db) -> Run:
    """Replace a run's whole to-do list."""
    find_run(db, run_id)
    todos = json.dumps([todo.model_dump() for todo in body.todos])
    db.execute("UPDATE runs SET todos = ? WHERE run_id = ?", (todos, run_id))
    return find_run(db, run_id)


@router.post("/runs/{run_id}/finish", operation_id="finish_run")
def finish_run(run_id: str, body: FinishIn, db: Db) -> Run:
    """Finish a running run with its summary for the handlers."""
    if find_run(db, run_id).status != "running":
        raise HTTPException(409, f"Run {run_id} is finished")
    db.execute(
        "UPDATE runs SET status = 'finished', summary = ?, finished_at = ?"
        " WHERE run_id = ?",
        (body.summary, now(), run_id),
    )
    return find_run(db, run_id)


@router.get("/runs/latest", operation_id="get_latest_run")
def get_latest_run(db: Db) -> Run | None:
    """Get the most recent run of the queue agent, or null before the first run."""
    row = db.execute("SELECT run_id FROM runs ORDER BY rowid DESC LIMIT 1").fetchone()
    return find_run(db, row["run_id"]) if row else None


@router.post("/queue/agent-runs", operation_id="run_queue_agent", status_code=202)
def run_queue_agent(body: CapIn, background: BackgroundTasks) -> QueueAgentRun:
    """Start the queue agent on the waiting claims; it works in the background."""
    run_id = uuid.uuid4().hex
    background.add_task(agent.work_queue, run_id, body.cap)
    return QueueAgentRun(run_id=run_id)
