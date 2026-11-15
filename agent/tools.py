"""The agent's tools, one for each API operation it may use, bound to one claim."""

from typing import Literal

from langchain_core.tools import BaseTool, tool

from agent import api
from agent.api import result, tool_reply

Document = Literal["policy_wording", "claims_manual"]


@tool
def list_sections(document: Document) -> str:
    """List the numbered sections of the policy wording or the claims manual, with
    the topics in each."""
    return tool_reply(api.list_sections(document))


@tool(response_format="content_and_artifact")
def read_section(document: Document, section: int) -> tuple[str, str | None]:
    """Read one numbered section of the policy wording or the claims manual."""
    response = api.read_section(document, section)
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
    claim = result(api.get_claim(claim_id))

    @tool
    def get_claim() -> str:
        """Get the claim in full: the story, the items claimed and the documents."""
        return tool_reply(api.get_claim(claim_id))

    @tool
    def get_policy() -> str:
        """Get the claim's policy: the plan, the add-ons, the trip and the travelers."""
        return tool_reply(api.get_policy(claim["policy_id"]))

    @tool
    def get_claim_history() -> str:
        """Get the customer's earlier claims."""
        return tool_reply(api.get_claim_history(claim["customer_id"]))

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
        return tool_reply(
            api.decide_claim(claim_id, outcome, payout, reasons, policy_section)
        )

    @tool
    def pay_claim(amount: float) -> str:
        """Pay the approved claim exactly its payout in US dollars."""
        return tool_reply(api.pay_claim(claim_id, amount))

    return [
        get_claim,
        get_policy,
        get_claim_history,
        list_sections,
        read_section,
        decide_claim,
        pay_claim,
    ]
