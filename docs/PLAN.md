# Plan: the claims pilot

This plan builds the pilot in `docs/SPEC.md`: a backend that holds the claims queue, a dashboard for the handlers, and the UnderCover Agent, which works each claim from the policy wording and the customer's records. It follows the stack in `docs/TECH_STACK.md`, the standards in `docs/CODE_STANDARDS.md` and the look in `docs/BRAND.md`.

## Choices in this plan

These are the calls I made where the spec leaves room. Review them before we build.

1. **Where the data lives.** The business records (customers, policies, plans, company settings and the policy wording) are read from the JSON and Markdown files in `data/` at request time. Only the claims' changing state is stored in SQLite: the decision, the payments, the sign-off and the activity log. The database file is created from `data/claims.json` on first start and is git-ignored.
2. **Queue states.** Each claim's state is worked out from what is stored, not stored itself:
   - *waiting*: no decision yet and no run in progress
   - *in progress*: the agent is working on it
   - *waiting for sign-off*: approved with a payout over $1,000 and not yet signed off
   - *decided*: declined, referred, or approved and signed off (or under the limit)
   A referred claim counts as *decided*, because the agent's job ends at the referral.
3. **Payments.** The agent pays an approval under $1,000 itself. For a payout over $1,000 it still tries to pay, and the backend refuses with a 409 until a handler signs off. That is how the spec's "even if the agent tries to pay" rule is met. "Paying" only records a payment in the database, since the spec says no real payments.
4. **Sign-off.** A handler signs off with a button on the claim. Without sign-in (per the spec), the sign-off records the time only.
5. **Running the agent.** The backend starts a run in a background thread, which calls `agent.main.run`. The agent then reads and writes through the backend's HTTP API, as the tech stack asks. The thread and the HTTP calls are separate, so there is no deadlock.
6. **Instructions.** The agent's instructions are the file `agent/instructions.md`. The backend serves them through `GET /api/agent/instructions`, the agent loads them through that route, and the dashboard shows them read only.
7. **Activity log.** Every tool call, decision, payment and run event is saved as an activity row. The claim page shows them in order.
8. **Not in this pilot.** `data/knowledge.json`, `data/claims_manual.md`, `data/security/`, and any scoring against `data/evals/`. The spec puts the claims manual out of scope. The evals are for checking the agent later, when you ask.
9. **What the agent sees.** The agent gets only what a decision needs: the claim, the policy terms (plan, add-ons, trip dates and the number of travelers), the policy wording and the claim history. It does not get the customer's name, email, phone, date of birth, address or nationality, or the travelers' names. Claim history keeps the claim ids, dates, types, outcomes and amounts. In the claim text, documents and history summaries, every known customer or traveler name is replaced with a role label ("the customer", "traveler 2"), and "Date of birth" and "Nationality" lines are dropped from documents. The agent reads through `/api/agent/...` routes, which build their own minimal view in `backend/agent_view.py`.
   - *The backend keeps the full details.* Decisions, payments, sign-offs, the activity log and the dashboard's views hold the real names and client details, since the handlers need them. The redaction applies only to what the agent receives, not to what the backend stores.
   - *What the agent gets back.* The responses the agent receives from `record_decision`, `pay_claim` and `add_event` carry no names either. They echo only ids, amounts and states.
   - *Limit:* redaction catches only the names listed in `data/customers.json` and `data/policies.json`. A name that appears only in a document, or a nickname, would get through to the agent. The test in phase 1 checks every claim against the listed names.

## Operations

Every operation has an `operation_id`, a one-line docstring and no optional inputs.

| Method and path | `operation_id` | Purpose |
|---|---|---|
| GET `/api/health` | `health` | Already built |
| GET `/api/claims` | `list_claims` | The queue, each claim with its state |
| GET `/api/claims/{claim_id}` | `get_claim` | One claim in full, for the dashboard: story, items, documents, the customer's name, the policy, state, decision and payments |
| GET `/api/agent/claims/{claim_id}` | `get_claim_for_agent` | What the agent sees: the claim with names redacted, the policy terms, the traveler count and the claim history without personal details |
| GET `/api/policy-wording` | `get_policy_wording` | The policy wording, as text |
| GET `/api/agent/instructions` | `get_agent_instructions` | The agent's instructions, as text |
| POST `/api/claims/{claim_id}/decision` | `record_decision` | Record approve, decline or refer, with payout, explanation and policy section |
| POST `/api/claims/{claim_id}/payments` | `pay_claim` | Pay an amount on an approved claim; blocked for an over-limit claim until signed off |
| POST `/api/claims/{claim_id}/sign-off` | `sign_off_claim` | A handler signs off a payout over $1,000 |
| POST `/api/claims/{claim_id}/events` | `add_event` | Add a step to the activity log |
| GET `/api/claims/{claim_id}/events` | `list_events` | The activity log for a claim, in order |
| POST `/api/claims/{claim_id}/run` | `run_claim` | Start the agent on one claim, in the background |
| POST `/api/runs` | `run_queue` | Start the agent on each waiting claim, one after another |

## Phase 1: the claims queue and its reading

**Builds.** `backend/db.py` creates the SQLite database from `data/claims.json` when it's empty. `backend/data.py` reads the customers, policies, plans, company settings and policy wording from `data/`. `backend/agent_view.py` builds the minimal view the agent gets, with the redaction in choice 9. The read operations are `list_claims`, `get_claim`, `get_claim_for_agent`, `get_policy_wording` and `get_agent_instructions`. `agent/instructions.md` holds a first draft of the instructions.

**Why.** Reading is the safe place to start: it lets us check the data before anything writes to it. Keeping reference data in the files, not in the database, keeps `data/` as the one source of truth, as the spec says. Building the agent's view in one module means the privacy rule lives in one place and is tested in one place.

**Success criteria**
- [x] `uv run pytest -q` passes, with coverage of at least 80%
- [x] `uv run pyright` and `uv run ruff check` and `uv run ruff format --check` pass
- [x] `curl -s localhost:8000/api/claims` returns 25 claims, each with `state` equal to `waiting`
- [x] `curl -s localhost:8000/api/claims/CLM-1001` returns the claim's story, its three items, its documents, the policy and the customer's name
- [x] `curl -s localhost:8000/api/agent/claims/CLM-1001` returns the plan `premium` with a `deductible` of 50, a `trip_delay_max` of 800 and a `traveler_count` of 1
- [x] `curl -s localhost:8000/api/agent/claims/CLM-1001` contains no customer name, email, phone, date of birth, address or nationality
- [x] A test loops over all 25 claims and checks that `/api/agent/claims/{id}` contains none of the customer or traveler names in `data/customers.json` and `data/policies.json`, and no "Date of birth" or "Nationality" line
- [x] `curl -s localhost:8000/api/claims/CLM-1001` still shows the customer's name, since the handlers see it
- [x] `curl -s localhost:8000/api/policy-wording` returns text that starts with "UnderCover Travel Insurance: Policy Wording"
- [x] `curl -s localhost:8000/api/claims/CLM-9999` returns 404
- [x] `curl -s localhost:8000/openapi.json` lists the operation_ids from the table above, each with a summary
- [x] `grep -r "evals" backend agent` finds nothing outside the tests

## Phase 2: decisions, payments and sign-off

**Builds.** The write operations `record_decision`, `pay_claim`, `sign_off_claim`, `add_event` and `list_events`. The decision rules: a claim takes one decision, a payout is zero unless the decision is approve, and a payout can't exceed the amount claimed. The payment rules: the claim must be approved, the amount can't exceed the payout, and a payout over the $1,000 limit needs a sign-off first, which gives a 409. Every write adds an activity row.

**Why.** The payment rule is the one hard rule in the spec, so the backend enforces it, not the agent or the dashboard. Putting it in the backend means no caller can get around it.

**Success criteria**
- [x] Tests cover each rule: a second decision is refused, a payout over the amount claimed is refused, a payment on a declined claim is refused, and a payment over $1,000 is refused until sign-off
- [x] `uv run pytest -q` passes, with coverage of at least 80%
- [x] `curl -s -X POST localhost:8000/api/claims/CLM-1001/decision -H "Content-Type: application/json" -d '{"decision":"approve","payout":420,"explanation":"...","policy_section":"3"}'` returns 200, and the claim's state becomes `decided`
- [x] `curl -s -X POST localhost:8000/api/claims/CLM-1001/payments -H "Content-Type: application/json" -d '{"amount":420}'` returns 200
- [x] On a claim approved for more than $1,000 (for example CLM-1002, which claims $1,150.00), `POST .../payments` returns 409 with a message that the claim is waiting for sign-off, and the state reads `waiting for sign-off`
- [x] After `POST .../sign-off`, the same payment returns 200
- [x] `curl -s localhost:8000/api/claims/CLM-1001/events` lists the decision and the payment, in that order
- [x] `npm run check:python` passes

## Phase 3: the agent's tools, instructions and entry point

**Builds.** The agent's tools in `agent/tools.py`, each a LangChain tool that calls one backend operation: `get_claim_for_agent`, `get_policy_wording`, `record_decision`, `pay_claim` and `add_event`. The agent has no tool that reaches the full dashboard view. `agent/main.py` loads the system prompt through `get_agent_instructions` and keeps the existing `run(claim_id, thread_id, llm=None)` signature. A callback writes each tool call to the activity log through `add_event`.

**Why.** The agent reaches the business only through the backend, so the rules in phase 2 apply to it, and what it does is visible on the claim. Tests run against a stub model, so a test never calls OpenRouter and never costs money.

**Success criteria**
- [ ] `uv run pytest -q` passes, with coverage of at least 80%. The tests use a stub chat model that returns scripted tool calls, and they never call OpenRouter
- [ ] A test runs the agent on CLM-1001 with a stub model that approves at 420 and pays. Afterwards the claim is `decided` with the payment recorded, and the activity log shows each tool call in order
- [ ] A test runs the agent on a claim over the limit, where the stub tries to pay. The payment is refused with 409 and the claim reads `waiting for sign-off`
- [ ] A test records every message the stub model receives during the CLM-1001 run, and none contains a customer or traveler name, an email, a phone number or a date of birth
- [ ] A test checks that the agent's tools call only `/api/agent/...` routes and the three write routes, never `/api/claims/{id}`
- [ ] A test checks that the responses of `record_decision`, `pay_claim` and `add_event`, as the agent receives them, contain no customer or traveler name
- [ ] A test checks that after the CLM-1001 run, `GET /api/claims/CLM-1001` still returns the customer's name, and the activity log is stored in full
- [ ] The agent's system prompt equals the text of `GET /api/agent/instructions` (a test checks this)
- [ ] `npm run check:python` passes

## Phase 4: running the agent from the backend

**Builds.** `run_claim` starts `agent.main.run` in a background thread, with a new thread id for each run, and returns 202 at once. While a run is going the claim reads `in progress`. A run that ends without a decision goes back to `waiting` and logs the error. `run_queue` runs each waiting claim, one at a time, to avoid bursts of model calls. A claim already in progress returns 409.

**Why.** An agent run takes a while, so the dashboard should not wait on it. One run at a time keeps the cost and the rate limits predictable.

**Success criteria**
- [ ] Tests cover: a run starts and returns 202; a second run on the same claim returns 409 while the first is going; a run that raises leaves the claim `waiting` with an error in its activity log
- [ ] `uv run pytest -q` passes, with coverage of at least 80%
- [ ] `curl -s -X POST localhost:8000/api/claims/CLM-1001/run` returns 202, and a `curl -s localhost:8000/api/claims/CLM-1001` shortly after shows `in progress`
- [ ] Live check, with the default model: once the run on CLM-1001 finishes, the claim has a decision with a payout no higher than its $420.00 claim, an explanation of two or three sentences with a policy section, and an activity log with the tool calls. The check reads only the decision the agent records, never `data/evals/`. This costs a few cents of OpenRouter credit. Use `MODEL_NAME=openrouter/free` to run it free
- [ ] `npm run check:python` passes

## Phase 5: the dashboard

**Builds.** Three screens, with hash routing and no router library:
- **Queue**: a table of the 25 claims with customer, claim type, amount claimed, state and decision. The state shows as a coloured chip (Sea Green, Marigold, Coral, Cerulean, with Raspberry for the sign-off state). A "Work the queue" button calls `run_queue`.
- **Claim**: the story, items, documents and policy summary; the decision, explanation and payout; the payment panel with a "Sign off" button for an over-limit payout and a "Pay" button; a "Run agent" button; and the activity log. The page polls every two seconds while the claim is `in progress`.
- **Instructions**: the agent's instructions, read only.

The brand is applied as in `docs/BRAND.md`: Instrument Sans for text, JetBrains Mono for claim numbers and amounts, rounded panels with no outline, money as "$1,250.00", and dark mode through the colors in the brand file.

**Why.** The handlers need to see the queue, each claim in full, and what the agent is doing on it, and the spec lists exactly those three screens.

**Success criteria**
- [ ] `npm run check:ts` passes, with coverage of at least 80%
- [ ] In the Playwright MCP browser at 1280 px wide, the queue shows 25 rows, and the state chips use the brand colors
- [ ] The claim page for CLM-1001 shows the story, the three items and the three documents, and the amounts read like "$420.00"
- [ ] At a phone width of 390 px, the queue and the claim page have no horizontal scroll (check `document.documentElement.scrollWidth` equals the viewport width)
- [ ] The claim page for an over-limit claim shows "Waiting for sign-off" and the "Pay" button is disabled until the sign-off is done
- [ ] The instructions page shows the text from `GET /api/agent/instructions` and has no edit controls
- [ ] In dark mode (set with `browser_emulate_media`), the page background is `#04232E` and the panels are black

## Phase 6: end-to-end tests and handover

**Builds.** Playwright tests in `e2e/` that start the backend on a test database, seeded fresh. They cover the queue, a claim page, and the sign-off rule: approve an over-limit claim through the API, see the payment blocked, sign off, and see it paid. The tests don't run the agent, so they never call a model. `docs/STATUS.md` describes what's built and how to run it.

**Why.** The sign-off rule is what the business will rely on most, so it gets an end-to-end test as well as unit tests. The agent has no end-to-end test because it needs a model; phase 4's live check covers it.

**Success criteria**
- [ ] `npm run e2e` passes
- [ ] The test database is a separate file from the development one, so running the tests never changes the queue you work from
- [ ] `docs/STATUS.md` lists the pilot's routes and says how to run it with `npm run dev`
- [ ] `npm run dev` starts the backend and the dashboard, and the dashboard's queue loads at `http://localhost:5173`
- [ ] `npm run check` passes, and I report its output in full
- [ ] `git status` shows no `.env`, no database file and no `data/evals/` changes

## Questions for you to decide

- **`data/evals/` is in git.** `git ls-files data/evals` lists its files, and `.gitignore` doesn't exclude it. The spec says the agent must never see it, and the backend and agent never read it. But anyone who clones the repo can read the answer key. Do you want it moved out of git, or is this fine for the course?
- **Choice 3 (payments).** I read the spec as "the agent pays approvals under $1,000, and over $1,000 it waits for sign-off." Is that right?
- **Choice 2 (refer).** I count a referred claim as *decided*. Should it have its own state for the handlers' queue?
