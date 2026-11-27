"""Runs the agent on claims in the background, so that a request returns at once."""

import threading
import uuid

from fastapi import HTTPException

from agent.main import run as run_agent
from backend import claims


def _work(claim_id: str) -> None:
    try:
        run_agent(claim_id, str(uuid.uuid4()))
    except Exception as error:
        claims.record_event(claim_id, "error", f"The agent run failed: {error}")
    else:
        if not claims.has_decision(claim_id):
            claims.record_event(
                claim_id, "error", "The agent finished without a decision."
            )
    finally:
        claims.finish_run(claim_id)


def _work_queue(claim_ids: list[str]) -> None:
    for claim_id in claim_ids:
        try:
            claims.start_run(claim_id)
        except HTTPException:
            continue
        _work(claim_id)


def start(claim_id: str) -> None:
    """Start the agent on one claim, in the background."""
    claims.start_run(claim_id)
    threading.Thread(target=_work, args=(claim_id,), daemon=True).start()


def start_queue() -> int:
    """Start the agent on each waiting claim, one after another. Return how many."""
    waiting = [row["claim_id"] for row in claims.queue() if row["state"] == "waiting"]
    threading.Thread(target=_work_queue, args=(waiting,), daemon=True).start()
    return len(waiting)
