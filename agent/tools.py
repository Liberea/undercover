"""The agent's tools, one for each API operation it may use."""

from typing import Literal

from langchain_core.tools import tool

from agent.api import request, tool_reply


@tool
def get_claim(claim_id: str) -> str:
    """Get a claim in full: the story, the items claimed and the documents."""
    return tool_reply(request("GET", f"/api/claims/{claim_id}", None))


@tool
def get_policy(policy_id: str) -> str:
    """Get a policy: the plan, the add-ons, the covered trip and the travelers."""
    return tool_reply(request("GET", f"/api/policies/{policy_id}", None))


@tool
def get_claim_history(customer_id: str) -> str:
    """Get the customer's earlier claims."""
    return tool_reply(request("GET", f"/api/customers/{customer_id}/claims", None))


@tool
def get_policy_wording() -> str:
    """Get the policy wording that every decision follows."""
    return tool_reply(request("GET", "/api/policy-wording", None))


@tool
def decide_claim(
    claim_id: str,
    outcome: Literal["approve", "decline", "refer"],
    payout: float,
    reasons: str,
    policy_section: str,
) -> str:
    """Record the decision on a claim: the outcome, the payout in US dollars (0 unless
    you approve), two or three sentences of reasons, and the policy wording section
    it rests on."""
    body = {
        "outcome": outcome,
        "payout": payout,
        "reasons": reasons,
        "policy_section": policy_section,
    }
    return tool_reply(request("POST", f"/api/claims/{claim_id}/decision", body))


@tool
def pay_claim(claim_id: str, amount: float) -> str:
    """Pay an approved claim exactly its payout in US dollars."""
    body = {"amount": amount}
    return tool_reply(request("POST", f"/api/claims/{claim_id}/payment", body))


TOOLS = [
    get_claim,
    get_policy,
    get_claim_history,
    get_policy_wording,
    decide_claim,
    pay_claim,
]
