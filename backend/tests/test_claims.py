from fastapi.testclient import TestClient

from backend import agent_view, data
from backend.main import app

client = TestClient(app)


def test_queue_lists_every_claim_as_waiting():
    rows = client.get("/api/claims").json()
    assert len(rows) == 25
    assert {row["state"] for row in rows} == {"waiting"}


def test_claim_view_shows_the_customer_and_policy():
    view = client.get("/api/claims/CLM-1001").json()
    assert view["customer"]["name"] == "Maya Patel"
    assert view["plan"]["plan"] == "premium"
    assert view["state"] == "waiting"
    assert view["decision"] is None
    assert view["paid_total"] == 0


def test_unknown_claim_is_not_found():
    assert client.get("/api/claims/CLM-9999").status_code == 404
    assert client.get("/api/agent/claims/CLM-9999").status_code == 404


def test_agent_view_of_a_claim_has_the_plan_terms():
    view = client.get("/api/agent/claims/CLM-1001").json()
    assert view["policy"]["plan"]["deductible"] == 50.0
    assert view["policy"]["plan"]["trip_delay_max"] == 800.0
    assert view["policy"]["traveler_count"] == 1
    assert "customer_id" not in view["claim"]


def test_agent_view_has_no_personal_details_for_any_claim():
    names = agent_view.person_names()
    for claim in data.claims():
        view = client.get(f"/api/agent/claims/{claim['claim_id']}").text
        for name in names:
            assert name not in view, claim["claim_id"]
        assert "Date of birth" not in view
        assert "Nationality" not in view
        assert "@" not in view
        assert "CUS-" not in view


def test_agent_view_labels_the_customer_and_the_travelers():
    view = client.get("/api/agent/claims/CLM-1023").text
    assert "the customer" in view
    assert "Colin Marsh" not in view
    assert "traveler " in view


def test_redaction_removes_date_of_birth_and_nationality():
    text = (
        "Patient: Ann Lee. Date of birth: February 3, 1965. "
        "Age: 61. Nationality: United States. Admitted."
    )
    redacted = agent_view._redact_text(text, {"Ann Lee": "the customer"})
    assert redacted == "Patient: the customer. Age: 61. Admitted."


def test_policy_wording_is_plain_text():
    response = client.get("/api/policy-wording")
    assert response.text.startswith("# UnderCover Travel Insurance: Policy Wording")
    assert response.headers["content-type"].startswith("text/plain")


def test_agent_instructions_are_plain_text():
    response = client.get("/api/agent/instructions")
    assert response.text.startswith("You are the UnderCover Agent.")


def test_every_operation_has_an_operation_id_and_summary():
    schema = client.get("/openapi.json").json()
    operations = [op for path in schema["paths"].values() for op in path.values()]
    assert {op["operationId"] for op in operations} == {
        "health",
        "list_claims",
        "get_claim",
        "get_claim_for_agent",
        "get_policy_wording",
        "get_agent_instructions",
        "record_decision",
        "pay_claim",
        "sign_off_claim",
        "add_event",
        "list_events",
    }
    assert all(op["summary"] for op in operations)
