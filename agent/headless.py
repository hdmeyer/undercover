"""Run the agent through the local Claude Code CLI, headless, with no API key.

Used when MODEL_NAME is claude-headless. The agent's tools are the same ones the
LangChain agent uses, wrapped as in-process tools for the Claude Agent SDK.
"""

import asyncio
from typing import Any

from claude_agent_sdk import (
    ClaudeAgentOptions,
    ResultMessage,
    create_sdk_mcp_server,
    query,
    tool,
)
from langchain_core.tools import BaseTool
from langchain_core.utils.pydantic import model_json_schema

from agent import tools

HEADLESS = "claude-headless"
MODEL = "claude-haiku-5-5"
SERVER = "undercover"


def _sdk_tool(lc_tool: BaseTool, claim_id: str) -> Any:
    """Wrap one LangChain tool as an SDK tool that also logs the call."""

    async def handler(args: dict[str, Any]) -> dict[str, Any]:
        tools._call(
            "POST",
            f"/api/claims/{claim_id}/events",
            {"text": f"Called {lc_tool.name} with {args}."},
        )
        return {"content": [{"type": "text", "text": lc_tool.invoke(args)}]}

    schema = model_json_schema(lc_tool.get_input_schema())
    return tool(lc_tool.name, lc_tool.description, schema)(handler)


def run(claim_id: str, instructions: str) -> str:
    """Run the agent on one claim through `claude` and return its final reply."""
    lc_tools = tools.make_tools(claim_id)
    server = create_sdk_mcp_server(
        SERVER, tools=[_sdk_tool(t, claim_id) for t in lc_tools]
    )
    options = ClaudeAgentOptions(
        model=MODEL,
        system_prompt=instructions,
        tools=[],
        mcp_servers={SERVER: server},
        allowed_tools=[f"mcp__{SERVER}__{t.name}" for t in lc_tools],
    )
    return asyncio.run(_ask(f"Work claim {claim_id}.", options))


async def _ask(prompt: str, options: ClaudeAgentOptions) -> str:
    reply = ""
    async for message in query(prompt=prompt, options=options):
        if isinstance(message, ResultMessage):
            reply = message.result or ""
    return reply
