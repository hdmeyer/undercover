"""The UnderCover backend."""

from typing import Any, Literal

from fastapi import FastAPI
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

from backend import agent_view, claims, data

app = FastAPI(title="UnderCover")


class DecisionIn(BaseModel):
    decision: Literal["approve", "decline", "refer"]
    payout: float
    explanation: str
    policy_section: str


class PaymentIn(BaseModel):
    amount: float


class EventIn(BaseModel):
    text: str


@app.get("/api/health", operation_id="health")
def health() -> dict[str, str]:
    """Check that the backend is running."""
    return {"status": "ok"}


@app.get("/api/claims", operation_id="list_claims")
def list_claims() -> list[dict[str, Any]]:
    """List the claims in the queue, with each claim's state."""
    return claims.queue()


@app.get("/api/claims/{claim_id}", operation_id="get_claim")
def get_claim(claim_id: str) -> dict[str, Any]:
    """Read one claim in full, for the handlers."""
    return claims.claim_view(claim_id)


@app.get("/api/agent/claims/{claim_id}", operation_id="get_claim_for_agent")
def get_claim_for_agent(claim_id: str) -> dict[str, Any]:
    """Read a claim as the agent sees it, without personal details."""
    claims.require_claim(claim_id)
    return agent_view.claim_for_agent(claim_id)


@app.get(
    "/api/policy-wording",
    operation_id="get_policy_wording",
    response_class=PlainTextResponse,
)
def get_policy_wording() -> str:
    """Read the policy wording that decides claims."""
    return data.policy_wording()


@app.get(
    "/api/agent/instructions",
    operation_id="get_agent_instructions",
    response_class=PlainTextResponse,
)
def get_agent_instructions() -> str:
    """Read the agent's instructions."""
    return data.agent_instructions()


@app.post("/api/claims/{claim_id}/decision", operation_id="record_decision")
def record_decision(claim_id: str, body: DecisionIn) -> dict[str, Any]:
    """Record a decision on a claim: approve, decline or refer."""
    return claims.record_decision(
        claim_id, body.decision, body.payout, body.explanation, body.policy_section
    )


@app.post("/api/claims/{claim_id}/payments", operation_id="pay_claim")
def pay_claim(claim_id: str, body: PaymentIn) -> dict[str, Any]:
    """Pay an amount on an approved claim, once any sign-off is in place."""
    return claims.pay_claim(claim_id, body.amount)


@app.post("/api/claims/{claim_id}/sign-off", operation_id="sign_off_claim")
def sign_off_claim(claim_id: str) -> dict[str, Any]:
    """Sign off a payout over the approval limit, so that it can be paid."""
    return claims.sign_off_claim(claim_id)


@app.post("/api/claims/{claim_id}/events", operation_id="add_event")
def add_event(claim_id: str, body: EventIn) -> dict[str, Any]:
    """Add a step to a claim's activity log."""
    return claims.add_event(claim_id, body.text)


@app.get("/api/claims/{claim_id}/events", operation_id="list_events")
def list_events(claim_id: str) -> list[dict[str, Any]]:
    """List a claim's activity log, oldest first."""
    return claims.list_events(claim_id)
