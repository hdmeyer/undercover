"""Claude Haiku 5.5 through the local Claude Code CLI, run headless with `claude -p`.

It uses the CLI's existing login, so no API key is needed.
"""

import subprocess

MODEL = "claude-haiku-5-5"


def predict(prompt: str) -> str:
    """Send one prompt to Claude Haiku 5.5 through `claude -p` and return its reply."""
    # A fixed argument list with no shell: the prompt is data, not a command.
    result = subprocess.run(  # noqa: S603
        ["claude", "-p", prompt, "--model", MODEL],  # noqa: S607
        capture_output=True,
        text=True,
        check=True,
        timeout=300,
    )
    return result.stdout.strip()
