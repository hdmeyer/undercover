# Status

The claims pilot from `docs/PLAN.md` is built.

- **Queue:** the backend reads the claims, customers, policies, plans, company settings and policy wording from `data/`. Each claim's state (waiting, in progress, waiting for sign-off or decided) is kept in `undercover.db`, created on first use and seeded from `data/claims.json`.
- **Decisions and payments:** a claim takes one decision, with a payout no more than its amount claimed. Payments can't total more than the payout, and a payout over $1,000 is refused until a handler signs it off. Every decision, payment and sign-off goes into the claim's activity log.
- **The agent:** `agent/` works one claim through the backend's API only. Its tools are `get_claim_for_agent`, `get_policy_wording`, `record_decision`, `pay_claim` and `add_event`. Its instructions come from `agent/instructions.md`, served at `GET /api/agent/instructions`. Each tool call is logged on the claim. The agent sees no customer or traveler names, emails, phone numbers or dates of birth. The backend keeps the full details.
- **Running the agent:** `POST /api/claims/{id}/run` runs one claim in the background, and `POST /api/runs` works through the waiting queue one claim at a time. A failed run is logged and the claim goes back to waiting.
- **Dashboard:** the queue, a claim page (story, items, documents, policy, decision, payments, activity log, with Run agent, Sign off and Pay), and the agent's instructions, read only. The look follows `docs/BRAND.md`, with dark mode.
- **Tests:** `npm run check` runs every check, including the Playwright tests in `e2e/`. Those tests start their own backend and dashboard on ports 8100 and 5174, with a fresh database in `e2e/test.db`, so they never touch `undercover.db`.

## Routes

- Backend: `/api/health`, `/api/claims`, `/api/claims/{id}`, `/api/claims/{id}/decision`, `/api/claims/{id}/payments`, `/api/claims/{id}/sign-off`, `/api/claims/{id}/events`, `/api/claims/{id}/run`, `/api/runs`, `/api/agent/claims/{id}`, `/api/agent/instructions` and `/api/policy-wording`. The API docs are at `/docs`.
- Dashboard: `#/` for the queue, `#/claims/{id}` for a claim, `#/instructions` for the agent's instructions.

## Running it

Run `uv sync` and `npm install` once, then `npm run dev`. The dashboard is at `http://localhost:5173` and the backend at `http://localhost:8000`.

The agent calls OpenRouter with the key in `.env`. To run it free, set `MODEL_NAME=openrouter/free`.

To run the agent on your local Claude Code CLI instead, with no API key, set `MODEL_NAME=claude-headless` in `.env`. The agent then runs Claude Haiku 5.5 through the Claude Agent SDK (`agent/headless.py`), which starts the `claude` command logged in on this machine, in place of the LangChain chat model over HTTP. The agent's tools and log entries are unchanged. Remove the line, or set another model, to go back to OpenRouter.

To call Claude Haiku 5.5 from code, use `agent/claude.py`: `from agent.claude import predict` and `predict(prompt)` runs `claude -p --model claude-haiku-5-5` and returns its reply.


## Testing outputs
 `npm run validate_outputs`. It compares the agent's decision and payout for each claim in the queue with the handlers' answers in data/evals/decisions.json, and prints the mismatches and totals.