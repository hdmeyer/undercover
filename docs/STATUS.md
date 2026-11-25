# Status

The pilot is being built from `docs/PLAN.md`. Phases done so far:

- **Phase 5, the dashboard:** three screens in `dashboard/`: the queue, a claim (its story, items, documents, policy, decision, payments, activity log, with Run agent, Sign off and Pay), and the agent's instructions, read only. Hash routes, no router library. The look follows `docs/BRAND.md`, with dark mode.
- **Phase 4, running the agent:** `POST /api/claims/{id}/run` starts the agent on one claim in the background, and `POST /api/runs` works through the waiting queue one claim at a time. While a run is going the claim reads `in progress`. A run that fails, or ends without a decision, is logged and the claim goes back to `waiting`. A live run on CLM-1001 with the default model was approved at $420.00 and paid.
- **Phase 3, the agent:** `agent/` works one claim through the backend's API only. Its tools are `get_claim_for_agent`, `get_policy_wording`, `record_decision`, `pay_claim` and `add_event`, each bound to the claim it's given. Its instructions come from `GET /api/agent/instructions`, and each tool call is logged on the claim. The tests use a stub model.
- **Phase 2, decisions and payments:** a claim takes one decision, with a payout no more than its amount claimed. Payments can't total more than the payout, and a payout over $1,000 is refused until a handler signs it off. Every decision, payment and sign-off is logged on the claim.
- **Phase 1, the claims queue:** the backend reads the claims, customers, policies, plans, company settings and policy wording from `data/`. Each claim's state is kept in `undercover.db`, created on first use and seeded from `data/claims.json`. The agent's view of a claim, `/api/agent/claims/{id}`, has its personal details removed.

Routes so far: `/api/health`, `/api/claims`, `/api/claims/{id}`, `/api/agent/claims/{id}`, `/api/policy-wording` and `/api/agent/instructions`, plus the write routes `/decision`, `/payments`, `/sign-off` and `/events` under each claim, and `/run` and `/api/runs` to start the agent. The API docs are at `/docs`. The agent reads its instructions from `agent/instructions.md`.

Run the dashboard at `http://localhost:5173` and the backend with `uv run -m uvicorn backend.main:app --reload`, or `npm run dev` once the dashboard is built.
