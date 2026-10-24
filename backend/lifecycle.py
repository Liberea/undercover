"""Moving a claim through its states: start, decide, pay and sign off."""

import sqlite3
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException

from backend.claims import claim, find_claim
from backend.db import Db
from backend.models import Claim, DecisionIn, PaymentIn, SignOffIn, StartIn
from backend.seed import load

router = APIRouter(prefix="/api/claims")

APPROVAL_LIMIT: float = load("company.json")["payout_approval_limit"]


def now() -> str:
    """Return the current time in UTC, to the second."""
    return datetime.now(UTC).isoformat(timespec="seconds")


def require_status(row: sqlite3.Row, *allowed: str) -> None:
    """Raise 409 unless the claim is in one of the allowed states."""
    if row["status"] not in allowed:
        state = row["status"].replace("_", " ")
        raise HTTPException(409, f"Claim {row['claim_id']} is {state}")


def set_status(db: sqlite3.Connection, claim_id: str, status: str) -> None:
    """Move a claim to a new state."""
    db.execute("UPDATE claims SET status = ? WHERE claim_id = ?", (status, claim_id))


@router.post("/{claim_id}/start", operation_id="start_claim")
def start_claim(claim_id: str, body: StartIn, db: Db) -> Claim:
    """Mark a waiting claim as in progress on the agent's thread."""
    require_status(find_claim(db, claim_id), "waiting", "in_progress")
    db.execute(
        "UPDATE claims SET status = 'in_progress', thread_id = ? WHERE claim_id = ?",
        (body.thread_id, claim_id),
    )
    return claim(find_claim(db, claim_id))


@router.post("/{claim_id}/release", operation_id="release_claim")
def release_claim(claim_id: str, db: Db) -> Claim:
    """Put a claim in progress back in the queue as waiting."""
    require_status(find_claim(db, claim_id), "in_progress")
    set_status(db, claim_id, "waiting")
    return claim(find_claim(db, claim_id))


@router.post("/{claim_id}/decision", operation_id="decide_claim")
def decide_claim(claim_id: str, body: DecisionIn, db: Db) -> Claim:
    """Approve, decline or refer a claim in progress, with the payout and reasons."""
    require_status(find_claim(db, claim_id), "in_progress")
    db.execute(
        "INSERT INTO decisions (claim_id, outcome, payout, reasons, policy_section,"
        " decided_at) VALUES (?, ?, ?, ?, ?, ?)",
        (
            claim_id,
            body.outcome,
            body.payout,
            body.reasons,
            body.policy_section,
            now(),
        ),
    )
    over_limit = body.outcome == "approve" and body.payout > APPROVAL_LIMIT
    set_status(db, claim_id, "waiting_for_sign_off" if over_limit else "decided")
    return claim(find_claim(db, claim_id))


@router.post("/{claim_id}/payment", operation_id="pay_claim")
def pay_claim(claim_id: str, body: PaymentIn, db: Db) -> Claim:
    """Pay an approved claim its payout; over the limit it needs a sign-off first."""
    row = find_claim(db, claim_id)
    if row["outcome"] != "approve":
        raise HTTPException(409, f"Claim {claim_id} has no approval to pay")
    if row["paid_amount"] is not None:
        raise HTTPException(409, f"Claim {claim_id} is already paid")
    if round(body.amount, 2) != round(row["payout"], 2):
        raise HTTPException(
            409,
            f"The approved payout is ${row['payout']:,.2f}, not ${body.amount:,.2f}",
        )
    if row["payout"] > APPROVAL_LIMIT:
        raise HTTPException(
            403, f"A payout over ${APPROVAL_LIMIT:,.2f} needs a handler's sign-off."
        )
    db.execute(
        "UPDATE decisions SET paid_amount = ?, paid_at = ? WHERE claim_id = ?",
        (body.amount, now(), claim_id),
    )
    return claim(find_claim(db, claim_id))


@router.post("/{claim_id}/sign-off", operation_id="sign_off_claim")
def sign_off_claim(claim_id: str, body: SignOffIn, db: Db) -> Claim:
    """Sign off a claim waiting for sign-off as a handler, which pays it."""
    row = find_claim(db, claim_id)
    require_status(row, "waiting_for_sign_off")
    handler = db.execute(
        "SELECT json_extract(data, '$.can_approve_over_limit') AS can_approve"
        " FROM handlers WHERE handler_id = ?",
        (body.handler_id,),
    ).fetchone()
    if handler is None:
        raise HTTPException(404, f"Handler {body.handler_id} not found")
    if not handler["can_approve"]:
        raise HTTPException(403, f"Handler {body.handler_id} cannot sign off")
    db.execute(
        "UPDATE decisions SET paid_amount = payout, paid_at = ?, signed_off_by = ?"
        " WHERE claim_id = ?",
        (now(), body.handler_id, claim_id),
    )
    set_status(db, claim_id, "decided")
    return claim(find_claim(db, claim_id))
