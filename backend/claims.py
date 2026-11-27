"""The claims queue: each claim's state, and what the dashboard shows of a claim."""

import sqlite3
from datetime import UTC, datetime
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


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _add_event(conn: sqlite3.Connection, claim_id: str, kind: str, text: str) -> None:
    conn.execute(
        "INSERT INTO events (claim_id, kind, text, created_at) VALUES (?, ?, ?, ?)",
        (claim_id, kind, text, _now()),
    )


def _paid_total(conn: sqlite3.Connection, claim_id: str) -> float:
    row = conn.execute(
        "SELECT COALESCE(SUM(amount), 0) AS total FROM payments WHERE claim_id = ?",
        (claim_id,),
    ).fetchone()
    return round(row["total"], 2)


def record_decision(
    claim_id: str, decision: str, payout: float, explanation: str, policy_section: str
) -> dict[str, Any]:
    """Record a claim's decision: approve, decline or refer, with its payout."""
    with connect() as conn:
        _claim_row(conn, claim_id)
        claimed = data.claim(claim_id)["amount_claimed"]
        if decision == "approve" and not 0 < payout <= claimed:
            raise HTTPException(
                422, f"An approval pays more than $0 and no more than ${claimed:,.2f}."
            )
        if decision != "approve" and payout != 0:
            raise HTTPException(422, "Only an approval has a payout.")
        if _decision(conn, claim_id) is not None:
            raise HTTPException(409, "This claim already has a decision.")
        conn.execute(
            "INSERT INTO decisions "
            "(claim_id, decision, payout, explanation, policy_section, decided_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (claim_id, decision, payout, explanation, policy_section, _now()),
        )
        _add_event(
            conn,
            claim_id,
            "decision",
            f"{decision.capitalize()}: payout ${payout:,.2f}. {explanation}",
        )
        return {
            "claim_id": claim_id,
            "decision": decision,
            "payout": payout,
            "state": state(conn, claim_id),
        }


def pay_claim(claim_id: str, amount: float) -> dict[str, Any]:
    """Pay part or all of an approved claim's payout."""
    with connect() as conn:
        _claim_row(conn, claim_id)
        decision = _decision(conn, claim_id)
        if decision is None or decision["decision"] != "approve":
            raise HTTPException(409, "Only an approved claim can be paid.")
        if awaiting_sign_off(decision):
            limit = data.company()["payout_approval_limit"]
            raise HTTPException(
                409, f"This payout is over ${limit:,.2f} and is waiting for sign-off."
            )
        paid = _paid_total(conn, claim_id)
        if amount <= 0 or round(paid + amount, 2) > round(decision["payout"], 2):
            raise HTTPException(
                409,
                f"The payments can't total more than ${decision['payout']:,.2f}.",
            )
        conn.execute(
            "INSERT INTO payments (claim_id, amount, paid_at) VALUES (?, ?, ?)",
            (claim_id, amount, _now()),
        )
        _add_event(conn, claim_id, "payment", f"Paid ${amount:,.2f}.")
        return {
            "claim_id": claim_id,
            "amount": amount,
            "paid_total": round(paid + amount, 2),
            "state": state(conn, claim_id),
        }


def sign_off_claim(claim_id: str) -> dict[str, Any]:
    """Sign off an approval over the payout limit, so that it can be paid."""
    with connect() as conn:
        _claim_row(conn, claim_id)
        decision = _decision(conn, claim_id)
        if decision is None or not awaiting_sign_off(decision):
            raise HTTPException(409, "This claim is not waiting for sign-off.")
        conn.execute(
            "UPDATE decisions SET signed_off_at = ? WHERE claim_id = ?",
            (_now(), claim_id),
        )
        _add_event(conn, claim_id, "sign_off", "Signed off by a handler.")
        return {"claim_id": claim_id, "state": state(conn, claim_id)}


def add_event(claim_id: str, text: str) -> dict[str, Any]:
    """Add a step to a claim's activity log."""
    with connect() as conn:
        _claim_row(conn, claim_id)
        _add_event(conn, claim_id, "step", text)
        return {"claim_id": claim_id, "text": text}


def list_events(claim_id: str) -> list[dict[str, Any]]:
    """Return a claim's activity log, oldest first."""
    with connect() as conn:
        _claim_row(conn, claim_id)
        return [
            dict(row)
            for row in conn.execute(
                "SELECT kind, text, created_at FROM events "
                "WHERE claim_id = ? ORDER BY id",
                (claim_id,),
            )
        ]


def has_decision(claim_id: str) -> bool:
    """Return True when the claim already has a decision."""
    with connect() as conn:
        return _decision(conn, claim_id) is not None


def record_event(claim_id: str, kind: str, text: str) -> None:
    """Add an event of any kind to a claim's activity log."""
    with connect() as conn:
        _add_event(conn, claim_id, kind, text)


def start_run(claim_id: str) -> None:
    """Mark a claim in progress, unless it is already in progress or decided."""
    require_claim(claim_id)
    with connect() as conn:
        started = conn.execute(
            "UPDATE claims SET running = 1 WHERE claim_id = ? AND running = 0 "
            "AND claim_id NOT IN (SELECT claim_id FROM decisions)",
            (claim_id,),
        ).rowcount
    if not started:
        raise HTTPException(409, "This claim is already in progress or decided.")


def finish_run(claim_id: str) -> None:
    """Mark a claim no longer in progress."""
    with connect() as conn:
        conn.execute("UPDATE claims SET running = 0 WHERE claim_id = ?", (claim_id,))
