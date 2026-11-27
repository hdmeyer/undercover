"""The agent's tools. Each one is a call to the UnderCover backend, for one claim."""

import os
from typing import Literal

import httpx
from langchain_core.tools import BaseTool, tool

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")


def backend() -> httpx.Client:
    """Return a client for the UnderCover backend."""
    return httpx.Client(base_url=BACKEND_URL, timeout=30)


def _call(method: str, path: str, body: dict[str, object] | None = None) -> str:
    with backend() as client:
        response = client.request(method, path, json=body)
    if response.is_error:
        return f"Refused ({response.status_code}): {response.text}"
    return response.text


def make_tools(claim_id: str) -> list[BaseTool]:
    """Return the agent's tools, each one bound to the claim being worked."""

    @tool
    def get_claim_for_agent() -> str:
        """Read the claim, its policy terms, its history and the company rules."""
        return _call("GET", f"/api/agent/claims/{claim_id}")

    @tool
    def get_policy_wording() -> str:
        """Read the policy wording that decides claims."""
        return _call("GET", "/api/policy-wording")

    @tool
    def record_decision(
        decision: Literal["approve", "decline", "refer"],
        payout: float,
        explanation: str,
        policy_section: str,
    ) -> str:
        """Record the decision on the claim.

        The payout is zero unless the decision is approve. The explanation is two
        or three sentences. The policy section is the number of the section that
        decides the claim.
        """
        return _call(
            "POST",
            f"/api/claims/{claim_id}/decision",
            {
                "decision": decision,
                "payout": payout,
                "explanation": explanation,
                "policy_section": policy_section,
            },
        )

    @tool
    def pay_claim(amount: float) -> str:
        """Pay an amount in US dollars on an approved claim."""
        return _call("POST", f"/api/claims/{claim_id}/payments", {"amount": amount})

    @tool
    def add_event(text: str) -> str:
        """Add a short note to the claim's activity log."""
        return _call("POST", f"/api/claims/{claim_id}/events", {"text": text})

    return [
        get_claim_for_agent,
        get_policy_wording,
        record_decision,
        pay_claim,
        add_event,
    ]
