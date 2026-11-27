import threading
import time

from fastapi.testclient import TestClient

from backend import claims, runs
from backend.main import app

client = TestClient(app)


def wait_until(check, timeout=10.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if check():
            return
        time.sleep(0.05)
    raise AssertionError("timed out waiting for the run")


def declining_agent(claim_id, thread_id):
    claims.record_decision(claim_id, "decline", 0.0, "Not covered.", "9")


def test_a_run_starts_in_the_background_and_records_the_decision(monkeypatch):
    monkeypatch.setattr(runs, "run_agent", declining_agent)
    response = client.post("/api/claims/CLM-1001/run")
    assert response.status_code == 202
    assert response.json() == {"claim_id": "CLM-1001", "state": "in progress"}
    wait_until(lambda: client.get("/api/claims/CLM-1001").json()["state"] == "decided")


def test_a_claim_cannot_run_twice_at_once(monkeypatch):
    release = threading.Event()

    def blocking_agent(claim_id, thread_id):
        release.wait(10)
        declining_agent(claim_id, thread_id)

    monkeypatch.setattr(runs, "run_agent", blocking_agent)
    assert client.post("/api/claims/CLM-1001/run").status_code == 202
    assert client.get("/api/claims/CLM-1001").json()["state"] == "in progress"
    assert client.post("/api/claims/CLM-1001/run").status_code == 409
    release.set()
    wait_until(lambda: client.get("/api/claims/CLM-1001").json()["state"] == "decided")


def test_a_decided_claim_cannot_be_run(monkeypatch):
    monkeypatch.setattr(runs, "run_agent", declining_agent)
    claims.record_decision("CLM-1001", "refer", 0.0, "Needs a handler.", "2")
    assert client.post("/api/claims/CLM-1001/run").status_code == 409


def test_a_failed_run_is_logged_and_the_claim_is_waiting_again(monkeypatch):
    def failing_agent(claim_id, thread_id):
        raise RuntimeError("the model is unavailable")

    monkeypatch.setattr(runs, "run_agent", failing_agent)
    client.post("/api/claims/CLM-1001/run")
    wait_until(lambda: client.get("/api/claims/CLM-1001").json()["state"] == "waiting")
    events = client.get("/api/claims/CLM-1001/events").json()
    assert events[-1]["kind"] == "error"
    assert "the model is unavailable" in events[-1]["text"]


def test_a_run_without_a_decision_is_logged(monkeypatch):
    monkeypatch.setattr(runs, "run_agent", lambda claim_id, thread_id: None)
    client.post("/api/claims/CLM-1001/run")
    wait_until(lambda: client.get("/api/claims/CLM-1001").json()["state"] == "waiting")
    events = client.get("/api/claims/CLM-1001/events").json()
    assert events[-1]["text"] == "The agent finished without a decision."


def test_the_queue_run_works_through_every_waiting_claim(monkeypatch):
    monkeypatch.setattr(runs, "run_agent", declining_agent)
    response = client.post("/api/runs")
    assert response.status_code == 202
    assert response.json() == {"waiting": 25}
    wait_until(
        lambda: all(
            row["state"] == "decided" for row in client.get("/api/claims").json()
        )
    )


def test_running_an_unknown_claim_is_not_found():
    assert client.post("/api/claims/CLM-9999/run").status_code == 404
