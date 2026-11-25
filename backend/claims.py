"""The claims queue: each claim's state, and what the dashboard shows of a claim."""

import sqlite3
from typing import Any

from fastapi import HTTPException

from backend import data
from backend.db import connect


def require_claim(claim_id: str) -> None:
    """Raise 404 unless the claim is in the queue."""
    with connect() as conn:
        _claim_row(conn, claim_id)


def _claim_row(conn: sqlite3.Connection, claim_id: str) -> sqlite3.Row:
    row = conn.execute(
        "SELECT * FROM claims WHERE claim_id = ?", (claim_id,)
    ).fetchone()
    if row is None:
        raise HTTPException(404, f"No claim {claim_id}.")
    return row


def _decision(conn: sqlite3.Connection, claim_id: str) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT * FROM decisions WHERE claim_id = ?", (claim_id,)
    ).fetchone()


def awaiting_sign_off(decision: sqlite3.Row) -> bool:
    """Return True when an approval over the limit is not yet signed off."""
    limit = data.company()["payout_approval_limit"]
    return (
        decision["decision"] == "approve"
        and decision["payout"] > limit
        and decision["signed_off_at"] is None
    )


def state(conn: sqlite3.Connection, claim_id: str) -> str:
    """Return where a claim stands: waiting, in progress, sign-off or decided."""
    if _claim_row(conn, claim_id)["running"]:
        return "in progress"
    decision = _decision(conn, claim_id)
    if decision is None:
        return "waiting"
    if awaiting_sign_off(decision):
        return "waiting for sign-off"
    return "decided"


def queue() -> list[dict[str, Any]]:
    """Return every claim in the queue with its state."""
    with connect() as conn:
        ids = [
            row["claim_id"]
            for row in conn.execute("SELECT claim_id FROM claims ORDER BY claim_id")
        ]
        rows = []
        for claim_id in ids:
            claim = data.claim(claim_id)
            decision = _decision(conn, claim_id)
            rows.append(
                {
                    "claim_id": claim_id,
                    "customer_name": data.customer(claim["customer_id"])["name"],
                    "claim_type": claim["claim_type"],
                    "amount_claimed": claim["amount_claimed"],
                    "state": state(conn, claim_id),
                    "decision": decision["decision"] if decision else None,
                    "payout": decision["payout"] if decision else None,
                }
            )
    return rows


def claim_view(claim_id: str) -> dict[str, Any]:
    """Return one claim in full, with its customer, policy, state and payments."""
    with connect() as conn:
        _claim_row(conn, claim_id)
        record = data.claim(claim_id)
        policy = data.policy(record["policy_id"])
        decision = _decision(conn, claim_id)
        payments = [
            dict(row)
            for row in conn.execute(
                "SELECT amount, paid_at FROM payments WHERE claim_id = ? ORDER BY id",
                (claim_id,),
            )
        ]
        return {
            "claim": record,
            "customer": data.customer(record["customer_id"]),
            "policy": policy,
            "plan": data.plan(policy["plan"]),
            "add_ons": data.add_ons_for(policy),
            "state": state(conn, claim_id),
            "decision": dict(decision) if decision else None,
            "payments": payments,
            "paid_total": round(sum(payment["amount"] for payment in payments), 2),
        }
