"""Reads UnderCover's business records from data/ and the agent's instructions."""

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent


def _json(name: str) -> Any:
    return json.loads((ROOT / "data" / name).read_text(encoding="utf-8"))


def _one(records: list[dict[str, Any]], key: str, value: str) -> dict[str, Any]:
    for record in records:
        if record[key] == value:
            return record
    raise KeyError(value)


def company() -> dict[str, Any]:
    return _json("company.json")


def claims() -> list[dict[str, Any]]:
    return _json("claims.json")


def claim(claim_id: str) -> dict[str, Any]:
    return _one(claims(), "claim_id", claim_id)


def policy(policy_id: str) -> dict[str, Any]:
    return _one(_json("policies.json"), "policy_id", policy_id)


def policies() -> list[dict[str, Any]]:
    return _json("policies.json")


def customer(customer_id: str) -> dict[str, Any]:
    return _one(customers(), "customer_id", customer_id)


def customers() -> list[dict[str, Any]]:
    return _json("customers.json")


def plan(name: str) -> dict[str, Any]:
    return _one(_json("plans.json")["plans"], "plan", name)


def add_ons_for(policy_record: dict[str, Any]) -> list[dict[str, Any]]:
    add_ons = _json("plans.json")["add_ons"]
    return [
        add_on for add_on in add_ons if add_on["add_on"] in policy_record["add_ons"]
    ]


def policy_wording() -> str:
    return (ROOT / "data" / "policy_wording.md").read_text(encoding="utf-8")


def agent_instructions() -> str:
    return (ROOT / "agent" / "instructions.md").read_text(encoding="utf-8")
