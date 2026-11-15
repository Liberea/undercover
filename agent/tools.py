"""The agent's tools, one for each API operation it may use, bound to one claim."""

from typing import Literal
from urllib.parse import quote

from langchain_core.tools import BaseTool, tool

from agent.api import call, request, tool_reply

Document = Literal["policy_wording", "claims_manual"]


def path(*parts: str) -> str:
    """Build an API path, escaping each part so an id can't add segments or a query."""
    return "/api/" + "/".join(quote(part, safe="") for part in parts)


@tool
def list_sections(document: Document) -> str:
    """List the numbered sections of the policy wording or the claims manual, with
    the topics in each."""
    return tool_reply(request("GET", path("documents", document, "sections"), None))


@tool(response_format="content_and_artifact")
def read_section(document: Document, section: int) -> tuple[str, str | None]:
    """Read one numbered section of the policy wording or the claims manual."""
    response = request(
        "GET", path("documents", document, "sections", str(section)), None
    )
    if not response.is_success:
        return tool_reply(response), None
    found = response.json()
    name = document.replace("_", " ").capitalize()
    heading = f"{name}, {section}. {found['title']}"
    return f"{heading}\n\n{found['text']}", heading


def tools_for(claim_id: str) -> list[BaseTool]:
    """Return the agent's tools, bound to this claim, its policy and its customer.

    The model passes no ids, so nothing in a claim can steer it to another record.
    """
    claim = call("GET", path("claims", claim_id), None)

    @tool
    def get_claim() -> str:
        """Get the claim in full: the story, the items claimed and the documents."""
        return tool_reply(request("GET", path("claims", claim_id), None))

    @tool
    def get_policy() -> str:
        """Get the claim's policy: the plan, the add-ons, the trip and the travelers."""
        return tool_reply(request("GET", path("policies", claim["policy_id"]), None))

    @tool
    def get_claim_history() -> str:
        """Get the customer's earlier claims."""
        customer_id = claim["customer_id"]
        return tool_reply(
            request("GET", path("customers", customer_id, "claims"), None)
        )

    @tool
    def decide_claim(
        outcome: Literal["approve", "decline", "refer"],
        payout: float,
        reasons: str,
        policy_section: str,
    ) -> str:
        """Record the decision on the claim: the outcome, the payout in US dollars
        (0 unless you approve), two or three sentences of reasons, and the policy
        wording section it rests on."""
        body = {
            "outcome": outcome,
            "payout": payout,
            "reasons": reasons,
            "policy_section": policy_section,
        }
        return tool_reply(request("POST", path("claims", claim_id, "decision"), body))

    @tool
    def pay_claim(amount: float) -> str:
        """Pay the approved claim exactly its payout in US dollars."""
        body = {"amount": amount}
        return tool_reply(request("POST", path("claims", claim_id, "payment"), body))

    return [
        get_claim,
        get_policy,
        get_claim_history,
        list_sections,
        read_section,
        decide_claim,
        pay_claim,
    ]
