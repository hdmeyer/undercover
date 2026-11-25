from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def decide(claim_id, decision="approve", payout=420.0):
    return client.post(
        f"/api/claims/{claim_id}/decision",
        json={
            "decision": decision,
            "payout": payout,
            "explanation": "The wording covers the trip delay.",
            "policy_section": "3",
        },
    )


def pay(claim_id, amount):
    return client.post(f"/api/claims/{claim_id}/payments", json={"amount": amount})


def test_a_decision_moves_the_claim_to_decided():
    response = decide("CLM-1001")
    assert response.status_code == 200
    assert response.json()["state"] == "decided"
    assert client.get("/api/claims/CLM-1001").json()["decision"]["payout"] == 420.0


def test_a_second_decision_is_refused():
    decide("CLM-1001")
    assert decide("CLM-1001").status_code == 409


def test_an_approval_cannot_pay_more_than_the_amount_claimed():
    assert decide("CLM-1001", payout=500.0).status_code == 422
    assert decide("CLM-1001", payout=0.0).status_code == 422


def test_a_decline_or_referral_has_no_payout():
    assert decide("CLM-1001", "decline", payout=100.0).status_code == 422
    response = decide("CLM-1001", "refer", payout=0.0)
    assert response.status_code == 200
    assert response.json()["state"] == "decided"


def test_a_declined_claim_cannot_be_paid():
    decide("CLM-1001", "decline", payout=0.0)
    response = pay("CLM-1001", 10.0)
    assert response.status_code == 409


def test_a_claim_without_a_decision_cannot_be_paid():
    assert pay("CLM-1001", 10.0).status_code == 409


def test_payments_cannot_total_more_than_the_payout():
    decide("CLM-1001")
    assert pay("CLM-1001", 300.0).json()["paid_total"] == 300.0
    assert pay("CLM-1001", 121.0).status_code == 409
    assert pay("CLM-1001", 0.0).status_code == 409
    assert pay("CLM-1001", 120.0).json()["paid_total"] == 420.0


def test_a_payout_over_the_limit_waits_for_sign_off():
    decide("CLM-1002", payout=1100.0)
    response = pay("CLM-1002", 1100.0)
    assert response.status_code == 409
    assert "waiting for sign-off" in response.json()["detail"]
    assert client.get("/api/claims/CLM-1002").json()["state"] == "waiting for sign-off"

    signed = client.post("/api/claims/CLM-1002/sign-off")
    assert signed.json()["state"] == "decided"
    assert pay("CLM-1002", 1100.0).status_code == 200


def test_a_payout_of_exactly_the_limit_needs_no_sign_off():
    decide("CLM-1002", payout=1000.0)
    assert pay("CLM-1002", 1000.0).status_code == 200


def test_sign_off_is_refused_when_nothing_is_waiting():
    assert client.post("/api/claims/CLM-1001/sign-off").status_code == 409
    decide("CLM-1001")
    assert client.post("/api/claims/CLM-1001/sign-off").status_code == 409


def test_the_activity_log_lists_the_decision_then_the_payment():
    decide("CLM-1001")
    pay("CLM-1001", 420.0)
    client.post("/api/claims/CLM-1001/events", json={"text": "Read the wording."})
    events = client.get("/api/claims/CLM-1001/events").json()
    assert [event["kind"] for event in events] == ["decision", "payment", "step"]
    assert events[0]["text"].startswith("Approve: payout $420.00.")
    assert events[2]["text"] == "Read the wording."


def test_unknown_claims_are_not_found():
    assert client.get("/api/claims/CLM-9999/events").status_code == 404
    assert (
        client.post("/api/claims/CLM-9999/events", json={"text": "x"}).status_code
        == 404
    )
    assert decide("CLM-9999").status_code == 404
    assert pay("CLM-9999", 1.0).status_code == 404
    assert client.post("/api/claims/CLM-9999/sign-off").status_code == 404
