"""The policies, customers' claim history, handlers and policy wording."""

import json
from pathlib import Path

from fastapi import APIRouter, HTTPException

from backend.db import Db
from backend.models import ClaimHistory, Handler, Policy, Text

router = APIRouter(prefix="/api")

POLICY_WORDING = Path(__file__).parent.parent / "data" / "policy_wording.md"
INSTRUCTIONS = Path(__file__).parent / "instructions.md"


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


@router.get("/policy-wording", operation_id="get_policy_wording")
def get_policy_wording() -> Text:
    """Get the policy wording that decisions follow."""
    return Text(text=POLICY_WORDING.read_text(encoding="utf-8"))


@router.get("/instructions", operation_id="get_instructions")
def get_instructions() -> Text:
    """Get the UnderCover Agent's instructions."""
    return Text(text=INSTRUCTIONS.read_text(encoding="utf-8"))
