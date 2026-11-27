"""Compare the agent's decisions on the queue with the handlers' in data/evals/."""

import json
import os
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
LABELS = ROOT / "data" / "evals" / "decisions.json"
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
HALF_A_CENT = 0.005


def main() -> None:
    text = LABELS.read_text(encoding="utf-8")
    labels = {label["claim_id"]: label for label in json.loads(text)}
    decided = decisions_match = both_match = 0
    with httpx.Client(base_url=BACKEND_URL, timeout=30) as client:
        for row in client.get("/api/claims").raise_for_status().json():
            claim_id = row["claim_id"]
            response = client.get(f"/api/claims/{claim_id}").raise_for_status()
            agent = response.json()["decision"]
            label = labels[claim_id]
            if agent is None:
                print(f"{claim_id}: no decision yet")
                continue
            decided += 1
            right_decision = agent["decision"] == label["decision"]
            right_payout = abs(agent["payout"] - label["payout"]) < HALF_A_CENT
            decisions_match += right_decision
            both_match += right_decision and right_payout
            if not (right_decision and right_payout):
                print(
                    f"{claim_id}: agent {agent['decision']} ${agent['payout']:,.2f}"
                    f" vs handlers {label['decision']} ${label['payout']:,.2f}"
                )
    print(f"\nDecided: {decided} of {len(labels)}")
    print(f"Decision matches: {decisions_match} of {decided}")
    print(f"Decision and payout matches: {both_match} of {decided}")


if __name__ == "__main__":
    main()
