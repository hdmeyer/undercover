"""The claim as the agent sees it: the same facts, with personal details removed."""

import re
from typing import Any

from backend import data

DROPPED = re.compile(r"(?:Date of birth|Nationality):[^.\n]*\.?\s*")


def person_names() -> set[str]:
    """Return every customer and traveler name in the records."""
    names = {customer["name"] for customer in data.customers()}
    names |= {
        traveler for policy in data.policies() for traveler in policy["travelers"]
    }
    return names


def _labels(policy: dict[str, Any], customer_name: str) -> dict[str, str]:
    labels = dict.fromkeys(person_names(), "another person")
    for number, traveler in enumerate(policy["travelers"], start=1):
        labels[traveler] = f"traveler {number}"
    labels[customer_name] = "the customer"
    return labels


def _redact_text(text: str, labels: dict[str, str]) -> str:
    text = DROPPED.sub("", text)
    names = sorted(labels, key=len, reverse=True)
    pattern = re.compile("|".join(re.escape(name) for name in names))
    return pattern.sub(lambda match: labels[match.group(0)], text)


def _redact(value: Any, labels: dict[str, str]) -> Any:
    if isinstance(value, str):
        return _redact_text(value, labels)
    if isinstance(value, list):
        return [_redact(item, labels) for item in value]
    if isinstance(value, dict):
        return {key: _redact(item, labels) for key, item in value.items()}
    return value


def claim_for_agent(claim_id: str) -> dict[str, Any]:
    """Return the claim, its policy terms and its history, without personal details."""
    record = data.claim(claim_id)
    policy = data.policy(record["policy_id"])
    customer = data.customer(record["customer_id"])
    view = {
        "claim": {key: value for key, value in record.items() if key != "customer_id"},
        "policy": {
            "plan": data.plan(policy["plan"]),
            "add_ons": data.add_ons_for(policy),
            "trip": policy["trip"],
            "traveler_count": len(policy["travelers"]),
        },
        "claim_history": customer["previous_claims"],
        "company": data.company(),
    }
    return _redact(view, _labels(policy, customer["name"]))
