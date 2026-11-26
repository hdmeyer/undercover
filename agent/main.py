"""The UnderCover Agent."""

import os
from typing import Any

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI
from pydantic import SecretStr

from agent import headless, tools

load_dotenv(override=True)

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_MODEL = "openai/gpt-6-luna"


class ActivityLog(BaseCallbackHandler):
    """Writes each tool call on a claim to the claim's activity log."""

    def __init__(self, claim_id: str) -> None:
        self.claim_id = claim_id

    def on_tool_start(
        self, serialized: dict[str, Any] | None, input_str: str, **kwargs: Any
    ) -> None:
        name = (serialized or {}).get("name", "tool")
        with tools.backend() as client:
            client.post(
                f"/api/claims/{self.claim_id}/events",
                json={"text": f"Called {name} with {input_str}."},
            )


def model() -> ChatOpenAI:
    """Return the model named in MODEL_NAME, or GPT-6 Luna by default."""
    name = os.getenv("MODEL_NAME")
    return ChatOpenAI(
        model=name or DEFAULT_MODEL,
        base_url=OPENROUTER_BASE_URL,
        api_key=SecretStr(os.environ["OPENROUTER_API_KEY"]),
        reasoning_effort=None if name else "low",
    )


def run(claim_id: str, thread_id: str, llm: BaseChatModel | None = None) -> str:
    """Run the agent on one claim and return its final reply."""
    with tools.backend() as client:
        instructions = client.get("/api/agent/instructions").text
    if os.getenv("MODEL_NAME") == headless.HEADLESS:
        return headless.run(claim_id, instructions)
    agent = create_agent(
        llm or model(),
        tools=tools.make_tools(claim_id),
        system_prompt=instructions,
    )
    result = agent.invoke(
        {"messages": [{"role": "user", "content": f"Work claim {claim_id}."}]},
        config={
            "configurable": {"thread_id": thread_id},
            "callbacks": [ActivityLog(claim_id)],
        },
    )
    return result["messages"][-1].text
