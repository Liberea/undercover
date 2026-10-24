"""The claims queue and each claim in full."""

import json
import sqlite3

from fastapi import APIRouter, HTTPException

from backend.db import Db
from backend.models import Claim, ClaimSummary, Decision, Payment

router = APIRouter(prefix="/api/claims")

CLAIM_QUERY = """
SELECT claims.*, customers.data AS customer, decisions.*, handlers.data AS handler
FROM claims
JOIN customers USING (customer_id)
LEFT JOIN decisions USING (claim_id)
LEFT JOIN handlers ON handlers.handler_id = decisions.signed_off_by
"""


def find_claim(db: sqlite3.Connection, claim_id: str) -> sqlite3.Row:
    """Return a claim's row, or raise 404."""
    row = db.execute(CLAIM_QUERY + "WHERE claim_id = ?", (claim_id,)).fetchone()
    if row is None:
        raise HTTPException(404, f"Claim {claim_id} not found")
    return row


def decision(row: sqlite3.Row) -> Decision | None:
    """Build a claim's decision and payment from its row."""
    if row["outcome"] is None:
        return None
    payment = None
    if row["paid_amount"] is not None:
        handler = row["handler"] and json.loads(row["handler"])["name"]
        payment = Payment(
            amount=row["paid_amount"], paid_at=row["paid_at"], signed_off_by=handler
        )
    return Decision(
        outcome=row["outcome"],
        payout=row["payout"],
        reasons=row["reasons"],
        policy_section=row["policy_section"],
        decided_at=row["decided_at"],
        payment=payment,
    )


def claim(row: sqlite3.Row) -> Claim:
    """Build a claim in full from its row."""
    return Claim.model_validate(
        json.loads(row["data"])
        | {
            "customer_name": json.loads(row["customer"])["name"],
            "status": row["status"],
            "thread_id": row["thread_id"],
            "decision": decision(row),
        }
    )


@router.get("", operation_id="list_claims")
def list_claims(db: Db) -> list[ClaimSummary]:
    """List the claims queue with where each claim stands."""
    rows = db.execute(CLAIM_QUERY + "ORDER BY claim_id").fetchall()
    return [
        ClaimSummary(
            claim_id=c.claim_id,
            customer_name=c.customer_name,
            claim_type=c.claim_type,
            submitted_on=c.submitted_on,
            amount_claimed=c.amount_claimed,
            status=c.status,
            outcome=c.decision and c.decision.outcome,
            payout=c.decision and c.decision.payout,
        )
        for c in map(claim, rows)
    ]


@router.get("/{claim_id}", operation_id="get_claim")
def get_claim(claim_id: str, db: Db) -> Claim:
    """Get a claim in full: the story, items, documents, status and decision."""
    return claim(find_claim(db, claim_id))
