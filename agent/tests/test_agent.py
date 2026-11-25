from fastapi.testclient import TestClient
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage

from agent import main, tools
from backend import agent_view
from backend.main import app


class StubModel(GenericFakeChatModel):
    """A chat model that gives scripted replies in place of a real model."""

    def bind_tools(self, tools, **kwargs):
        return self


def recording_model(replies, seen):
    """Return a stub model that also keeps every message it is sent."""

    class Recording(StubModel):
        def _generate(self, messages, stop=None, run_manager=None, **kwargs):
            seen.extend(messages)
            return super()._generate(messages, stop, run_manager, **kwargs)

    return Recording(messages=iter(replies))


def call(name, args):
    return AIMessage(content="", tool_calls=[{"name": name, "args": args, "id": name}])


class SpyClient(TestClient):
    """A test client that keeps the path of every request."""

    def __init__(self, app):
        super().__init__(app)
        self.paths: list[str] = []

    def request(self, method, url, *args, **kwargs):
        self.paths.append(url)
        return super().request(method, url, *args, **kwargs)


def use_backend(monkeypatch):
    client = SpyClient(app)
    monkeypatch.setattr(tools, "backend", lambda: client)
    return client


def test_the_agent_decides_and_pays_a_routine_claim(monkeypatch):
    client = use_backend(monkeypatch)
    replies = [
        call("get_claim_for_agent", {}),
        call("get_policy_wording", {}),
        call(
            "record_decision",
            {
                "decision": "approve",
                "payout": 420.0,
                "explanation": (
                    "The trip delay is covered. The payout covers the hotel, "
                    "meals and taxis."
                ),
                "policy_section": "3",
            },
        ),
        call("pay_claim", {"amount": 420.0}),
        AIMessage(content="Approved and paid $420.00."),
    ]
    seen = []
    reply = main.run("CLM-1001", "thread-1", recording_model(replies, seen))

    assert reply == "Approved and paid $420.00."
    claim = client.get("/api/claims/CLM-1001").json()
    assert claim["state"] == "decided"
    assert claim["paid_total"] == 420.0
    texts = [
        event["text"] for event in client.get("/api/claims/CLM-1001/events").json()
    ]
    called = [text.split(" with ")[0] for text in texts if text.startswith("Called")]
    assert called == [
        "Called get_claim_for_agent",
        "Called get_policy_wording",
        "Called record_decision",
        "Called pay_claim",
    ]


def test_a_payout_over_the_limit_is_refused_until_sign_off(monkeypatch):
    client = use_backend(monkeypatch)
    replies = [
        call("get_claim_for_agent", {}),
        call(
            "record_decision",
            {
                "decision": "approve",
                "payout": 1100.0,
                "explanation": "Covered.",
                "policy_section": "5",
            },
        ),
        call("pay_claim", {"amount": 1100.0}),
        AIMessage(content="Approved. The payment waits for sign-off."),
    ]
    seen = []
    main.run("CLM-1002", "thread-2", recording_model(replies, seen))

    assert client.get("/api/claims/CLM-1002").json()["state"] == "waiting for sign-off"
    results = [str(message.content) for message in seen]
    assert any("Refused (409)" in result and "sign-off" in result for result in results)


def test_the_model_sees_no_personal_details(monkeypatch):
    use_backend(monkeypatch)
    replies = [
        call("get_claim_for_agent", {}),
        call("get_policy_wording", {}),
        AIMessage(content="Referred for more information."),
    ]
    seen = []
    main.run("CLM-1016", "thread-3", recording_model(replies, seen))

    text = " ".join(str(message.content) for message in seen)
    for name in agent_view.person_names():
        assert name not in text
    assert "@" not in text
    assert "Date of birth" not in text
    assert "CUS-" not in text


def test_the_system_prompt_is_the_instructions_from_the_backend(monkeypatch):
    client = use_backend(monkeypatch)
    replies = [AIMessage(content="Nothing to do.")]
    seen = []
    main.run("CLM-1001", "thread-4", recording_model(replies, seen))

    instructions = client.get("/api/agent/instructions").text
    assert seen[0].content == instructions


def test_the_agent_only_calls_its_own_routes(monkeypatch):
    client = use_backend(monkeypatch)
    replies = [
        call("get_claim_for_agent", {}),
        call("get_policy_wording", {}),
        AIMessage(content="Referred."),
    ]
    main.run("CLM-1001", "thread-5", recording_model(replies, []))

    assert "/api/claims/CLM-1001" not in client.paths
    assert "/api/agent/claims/CLM-1001" in client.paths


def test_model_name(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.delenv("MODEL_NAME", raising=False)
    assert main.model().model_name == "openai/gpt-6-luna"
    monkeypatch.setenv("MODEL_NAME", "openrouter/free")
    assert main.model().model_name == "openrouter/free"
