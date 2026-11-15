"""The policies, the customers' claim history and the handlers."""

import json

from fastapi import APIRouter, HTTPException

from backend.db import Db
from backend.models import ClaimHistory, Handler, Policy

router = APIRouter(prefix="/api")


@router.get("/policies/{policy_id}", operation_id="get_policy")
def get_policy(policy_id: str, db: Db) -> Policy:
    """Get a policy: the plan, add-ons, trip and travelers."""
    row = db.execute(
        "SELECT data FROM policies WHERE policy_id = ?", (policy_id,)
    ).fetchone()
    if row is None:
        raise HTTPException(404, f"Policy {policy_id} not found")
    return Policy.model_validate_json(row["data"])


@router.get("/customers/{customer_id}/claims", operation_id="get_claim_history")
def get_claim_history(customer_id: str, db: Db) -> ClaimHistory:
    """Get a customer's earlier claims, without their contact details."""
    row = db.execute(
        "SELECT data FROM customers WHERE customer_id = ?", (customer_id,)
    ).fetchone()
    if row is None:
        raise HTTPException(404, f"Customer {customer_id} not found")
    return ClaimHistory.model_validate_json(row["data"])


@router.get("/handlers", operation_id="list_handlers")
def list_handlers(db: Db) -> list[Handler]:
    """List the claims handlers."""
    rows = db.execute("SELECT data FROM handlers ORDER BY handler_id").fetchall()
    return [Handler.model_validate(json.loads(row["data"])) for row in rows]
