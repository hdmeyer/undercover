"""The UnderCover backend."""

from typing import Any

from fastapi import FastAPI
from fastapi.responses import PlainTextResponse

from backend import agent_view, claims, data

app = FastAPI(title="UnderCover")


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
