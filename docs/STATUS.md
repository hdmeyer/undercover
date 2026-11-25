# Status

The pilot is being built from `docs/PLAN.md`. Phases done so far:

- **Phase 3, the agent:** `agent/` works one claim through the backend's API only. Its tools are `get_claim_for_agent`, `get_policy_wording`, `record_decision`, `pay_claim` and `add_event`, each bound to the claim it's given. Its instructions come from `GET /api/agent/instructions`, and each tool call is logged on the claim. The tests use a stub model.
- **Phase 2, decisions and payments:** a claim takes one decision, with a payout no more than its amount claimed. Payments can't total more than the payout, and a payout over $1,000 is refused until a handler signs it off. Every decision, payment and sign-off is logged on the claim.
- **Phase 1, the claims queue:** the backend reads the claims, customers, policies, plans, company settings and policy wording from `data/`. Each claim's state is kept in `undercover.db`, created on first use and seeded from `data/claims.json`. The agent's view of a claim, `/api/agent/claims/{id}`, has its personal details removed.

Routes so far: `/api/health`, `/api/claims`, `/api/claims/{id}`, `/api/agent/claims/{id}`, `/api/policy-wording` and `/api/agent/instructions`, plus the write routes `/decision`, `/payments`, `/sign-off` and `/events` under each claim. The API docs are at `/docs`. The agent reads its instructions from `agent/instructions.md`.

Run the backend with `uv run -m uvicorn backend.main:app --reload`, or `npm run dev` once the dashboard is built.
