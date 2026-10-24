# Plan: the claims pilot

This plan builds the pilot in `docs/SPEC.md`: a backend that holds the claims queue, the UnderCover Agent that decides claims through the backend's API, and a dashboard where the handlers watch the queue, follow the agent's work and sign off large payouts.

It follows `docs/TECH_STACK.md`, `docs/CODE_STANDARDS.md`, `docs/PROCESS.md` and `docs/BRAND.md`. It adds no new dependencies: everything it needs is already in `pyproject.toml` and `package.json`.

## How it fits together

```
  Handler's browser                                   OpenRouter
  +--------------------+                              +-----------+
  | Dashboard          |                              | the model |
  | React, Vite, TS    |                              +-----^-----+
  +---------+----------+                                    |
            | /api, polled every 1-2 s                      |
  +---------v-------------------+     HTTP API      +-------+--------+
  | Backend: FastAPI + SQLite   |<------------------| UnderCover     |
  | seeded from data/           |  reads, decides,  | Agent          |
  | (never data/evals/)         |  pays, logs steps | create_agent   |
  |                             |------------------>|                |
  +-----------------------------+   starts a run    +----------------+
```

- **The backend is the only place with data.** It builds a SQLite database from `data/` on first start. The agent and the dashboard both work through its API.
- **The agent never touches the database or `data/`.** Each of its tools wraps one API operation, named after that operation's `operation_id`. It gets its instructions from the API too.
- **The backend enforces the rules.** The $1,000 sign-off limit is checked inside the `pay_claim` operation, so it holds whatever the model does.

### The claim's states

```
 waiting --start_claim--> in progress --decide_claim--> decided
    ^                         |   \
    |                         |    `--decide_claim, approve over $1,000--> waiting for sign-off
    `------release_claim------'                                                 |
     (the run failed or ended                                    sign_off_claim (pays)
      without a decision)                                                       |
                                                                                v
                                                                             decided
```

The seed data has every claim as `open`; the seed stores them as `waiting`.

### The payment rules

`pay_claim(claim_id, amount)` pays only when all of these hold. Otherwise it refuses and pays nothing:

| Rule | Refusal |
|---|---|
| The claim has an approve decision | 409 |
| The amount equals the approved payout | 409 |
| The claim has not been paid yet | 409 |
| The amount is $1,000.00 or less, or a handler has signed off | 403, "A payout over $1,000.00 needs a handler's sign-off." |

`sign_off_claim(claim_id, handler_id)` is the handler's action: it works only on a claim waiting for sign-off, records which handler signed off, releases the payment and marks the claim decided. The limit comes from `payout_approval_limit` in `data/company.json`.

### The API

Every operation has an `operation_id`, a one-line docstring and only required inputs, as `docs/TECH_STACK.md` asks. The agent's tools carry the same names.

| `operation_id` | Route | Used by |
|---|---|---|
| `health` | `GET /api/health` | checks (exists) |
| `list_claims` | `GET /api/claims` | dashboard |
| `get_claim` | `GET /api/claims/{claim_id}` | agent tool, dashboard |
| `get_policy` | `GET /api/policies/{policy_id}` | agent tool, dashboard |
| `get_claim_history` | `GET /api/customers/{customer_id}/claims` | agent tool, dashboard |
| `get_policy_wording` | `GET /api/policy-wording` | agent tool |
| `get_instructions` | `GET /api/instructions` | agent, dashboard |
| `list_handlers` | `GET /api/handlers` | dashboard |
| `start_claim` | `POST /api/claims/{claim_id}/start` | agent |
| `release_claim` | `POST /api/claims/{claim_id}/release` | agent |
| `add_step` | `POST /api/claims/{claim_id}/steps` | agent |
| `list_steps` | `GET /api/claims/{claim_id}/steps` | dashboard |
| `decide_claim` | `POST /api/claims/{claim_id}/decision` | agent tool |
| `pay_claim` | `POST /api/claims/{claim_id}/payment` | agent tool |
| `sign_off_claim` | `POST /api/claims/{claim_id}/sign-off` | dashboard |
| `run_agent` | `POST /api/claims/{claim_id}/agent-runs` | dashboard |

The model sees six tools: `get_claim`, `get_policy`, `get_claim_history`, `get_policy_wording`, `decide_claim` and `pay_claim`. Starting, releasing and logging steps are done by the agent's own code, not the model. Signing off is the handler's action, so the agent has no tool for it.

### Key choices and why

1. **SQLite through Python's built-in `sqlite3`, with JSON columns.** A claim's story, items and documents are stored as JSON, next to plain columns for what we filter and update (status, ids, amounts). Six small tables (claims, policies, customers, handlers, decisions with their payment and sign-off, and steps) are enough for the pilot, and nothing needs an ORM yet.
2. **The decision is a tool call with structured arguments.** `decide_claim(claim_id, outcome, payout, reasons, policy_section)` checks `outcome` against approve, decline and refer and requires a payout of 0 unless the outcome is approve. We never parse the model's free text for the decision.
3. **The backend's refusals go back to the model as text.** I checked this with a stub model: `create_agent` stops the whole run when a tool raises. So when the backend refuses (a 4xx), the tool returns its message, such as "needs a handler's sign-off", and the agent can carry on and report it.
4. **Steps are streamed and polled.** The agent streams with `stream_mode="updates"` (checked: it yields a `model` update for each tool call or reply and a `tools` update for each result) and posts each one through `add_step`. The dashboard polls `list_steps` every second while the claim is in progress. Polling is simpler than websockets or server-sent events and fast enough to watch the agent work.
5. **The dashboard starts the agent through the backend.** `run_agent` gives the run a new thread id and starts `agent.run(claim_id, thread_id)` in a FastAPI background task. The agent still reaches the backend only over HTTP. There is also a command line: `uv run -m agent CLM-1001` for one claim, and `uv run -m agent` to work through every waiting claim.
6. **A run never leaves a claim stuck.** If a run fails, or ends without calling `decide_claim`, the agent records why as a step and calls `release_claim`, which puts the claim back to waiting.
7. **The customer's personal data stays out of the agent's view.** `get_claim_history` returns the customer's name, customer-since date and earlier claims, but not their email, phone, address or date of birth, since the decision doesn't need them.
8. **The answer key never enters the system.** The seed reads only `claims.json`, `policies.json`, `customers.json` and `handlers.json`; the backend also reads `company.json`, `policy_wording.md` and its own `backend/instructions.md`. Nothing in `backend/` or `agent/` names `data/evals/`.
9. **End-to-end tests get their own servers and a fresh database.** The tests change claims, so Playwright starts its own backend on port 8100 with a fresh database and its own dashboard on port 5180. They never touch your dev data, and they can run again and again. Since tests never call a model, the end-to-end tests play the agent's part through the API: they start a claim, post steps, decide and pay, then check what the dashboard shows.
10. **No router or Markdown library in the dashboard.** Three views (`#/`, `#/claims/<id>`, `#/instructions`) are handled with the URL hash in a few lines, so links and the back button work. The instructions are shown as preformatted text.

## Phase 1: The database and the read operations

**What it builds.** `backend/db.py` holds the connection and the schema. `backend/seed.py` loads `data/` into the database: the backend creates and seeds it on startup if the file is missing, and `uv run -m backend.seed` rebuilds it from scratch. The database lives in `backend/undercover.db`, or in the path in `UNDERCOVER_DB` when that is set (for tests). The read operations are `list_claims`, `get_claim`, `get_policy`, `get_claim_history`, `get_policy_wording` and `list_handlers`, in short route modules (`backend/claims.py`, `backend/records.py`) that `backend/main.py` includes.

**Why first.** Everything else reads from or writes to these records, and the read API is what the agent's tools will wrap.

**Success criteria**

- [x] `uv run pytest backend` passes, with tests for each operation, including a 404 for an unknown claim, policy and customer.
- [x] `uv run -m backend.seed` prints the counts it loaded: 25 claims, 50 policies, 49 customers, 3 handlers.
- [x] With the backend running, `GET /api/claims` returns 25 claims, all with status `waiting`, each with its id, customer name, claim type, amount claimed and submitted date.
- [x] `GET /api/claims/CLM-1001` returns the full claim: the story, 3 items, 4 documents, status `waiting` and no decision.
- [x] `GET /api/claims/CLM-9999` returns 404.
- [x] `GET /api/customers/CUS-3001/claims` returns Maya Patel's history with CLM-0412, and no email, phone, address or date of birth.
- [x] `GET /api/policy-wording` returns the text of `data/policy_wording.md`.
- [x] `GET /api/handlers` returns the three handlers.
- [x] A test walks `app.openapi()` and checks that every operation has an `operation_id`, a one-line description and no optional parameters or body fields.
- [x] `git grep --untracked -n "evals" -- backend agent` finds nothing (`--untracked`, since new files are not in git yet).
- [x] `npm run check:python` passes with coverage at 80% or more.

## Phase 2: Decisions, payments and the sign-off rule

**What it builds.** The operations that move a claim through its states: `start_claim` (records the thread id), `release_claim`, `decide_claim`, `pay_claim` and `sign_off_claim`, with the rules in the tables above. `list_claims` and `get_claim` now include the decision and the payment.

**Why now.** These rules, above all the $1,000 limit, are the heart of the spec. Building them in the backend before there is an agent proves that they hold no matter what the agent does.

**Success criteria**

- [x] Tests cover every transition and every refusal: deciding a claim that isn't in progress (409), a decline or refer with a payout other than 0 (422), an unknown outcome (422), paying without an approval (409), paying a different amount from the approved payout (409), paying twice (409), paying over the limit before sign-off (403), signing off a claim that isn't waiting for sign-off (409) and an unknown handler (404).
- [x] On a freshly seeded database, these API calls give these responses:
  - [x] `start_claim` CLM-1001, `decide_claim` approve $420.00, `pay_claim` $420.00: 200, and the claim is `decided` with a payment of $420.00 and no sign-off.
  - [x] `start_claim` CLM-1002, `decide_claim` approve $1,150.00: the claim is `waiting_for_sign_off`.
  - [x] `pay_claim` CLM-1002 $1,150.00: 403 with "A payout over $1,000.00 needs a handler's sign-off.", and `get_claim` shows no payment.
  - [x] `sign_off_claim` CLM-1002 by HND-01: the claim is `decided`, paid $1,150.00, signed off by Dana Whitfield.
  - [x] `pay_claim` CLM-1002 again: 409, already paid.
- [x] `uv run -m backend.seed` puts every claim back to `waiting`.
- [x] `npm run check:python` passes with coverage at 80% or more.

## Phase 3: The UnderCover Agent

**What it builds.**

- `backend/instructions.md`, the agent's instructions, served by `get_instructions`. They tell the agent, in plain words, to read the claim, the policy, the customer's claim history and the policy wording; to decide by the policy wording alone; to refer a claim that needs someone's judgment or a missing document; to work out the payout as section 10 of the wording describes; to record the decision with two or three sentences of reasons and the policy section; and to pay an approved claim, knowing a payout over $1,000 waits for a handler's sign-off.
- `add_step`, `list_steps` and `run_agent` in the backend.
- `agent/tools.py`: the six tools, each a thin wrapper over one API operation, which return the backend's refusals as text.
- `agent/main.py`: `run(claim_id, thread_id)` fetches the instructions, calls `start_claim`, streams the agent and posts each step (a tool call, a tool result, the final reply or an error). If the claim is still in progress at the end, it records why and calls `release_claim`. The model is GPT-6 Luna with low reasoning effort, or the model in `MODEL_NAME`, as now.
- `agent/__main__.py`: `uv run -m agent CLM-1001` runs one claim; `uv run -m agent` works through every waiting claim in turn.

**Why now.** With the rules in place, the agent can be built and tested against the real backend (through FastAPI's `TestClient`) with a stub model, so the tests cost nothing and never call a model.

**Success criteria**

- [ ] `uv run pytest agent` passes, with a stub model, for these runs:
  - [ ] An approval under the limit: the stub reads CLM-1001, decides approve $420.00 and pays. The claim is `decided`, paid, and its steps list each tool call, each result and the final reply in order.
  - [ ] An approval over the limit where the agent tries to pay anyway: the `pay_claim` tool returns the backend's refusal as text, nothing is paid, and the claim is `waiting_for_sign_off`.
  - [ ] A run that ends without a decision: the claim is back to `waiting`, and the last step says the run ended without a decision.
  - [ ] A run where the model raises an error: the claim is back to `waiting`, the error is a step, and the error is raised again.
  - [ ] The model receives the text from `GET /api/instructions` as its system prompt.
- [ ] A backend test checks that `run_agent` returns 202 with a thread id and starts the run (with the run replaced by a stub).
- [ ] The existing test of the model name still passes: GPT-6 Luna by default, `MODEL_NAME` when it's set.
- [ ] One real run, with the backend running: `uv run -m agent CLM-1001` prints the agent's reply, `GET /api/claims/CLM-1001` shows a decision with an outcome, a payout, two or three sentences of reasons and a policy section, and `GET /api/claims/CLM-1001/steps` lists the steps. This uses the model in `MODEL_NAME` if it's set, otherwise GPT-6 Luna, and costs a cent or two at most. Then `uv run -m backend.seed` resets the database.
- [ ] `npm run check:python` passes with coverage at 80% or more.

## Phase 4: The dashboard's look and the queue

**What it builds.**

- `dashboard/src/styles.css` with the brand as CSS variables: dark by default and light on request, Geist and Geist Mono from Google Fonts, `font-synthesis: none`, the type scale, cards, buttons, hairline outlines and the gradient for the product name and the primary button.
- The app's frame: a rounded top bar with the product name, links to the queue and the instructions, and a light and dark switch that's remembered in the browser. The three views are switched with the URL hash.
- `dashboard/src/api.ts` with typed functions for the API and `dashboard/src/format.ts` for money, such as $1,250.00.
- The queue: a count of claims in each state at the top, then a table with the claim id, customer, claim type, submitted date, amount claimed, status and decision. It refreshes every two seconds. The status pills use the brand order: waiting warm, in progress mid, decided cool, and waiting for sign-off in Alert, since it needs a handler.
- The end-to-end setup from key choice 9: `playwright.config.ts` starts a backend on port 8100 with a fresh database and a dashboard on port 5180, and `vite.config.ts` reads the backend's address from `BACKEND_URL`, defaulting to port 8000. `e2e/queue.spec.ts` replaces `e2e/health.spec.ts`.

**Why now.** With the backend and the agent working, the dashboard can be built against real data. The brand and the frame come first, so every later screen inherits them.

**Success criteria**

- [ ] Vitest tests pass for the queue (rows, counts and status labels from a stubbed API), the money format and the theme switch.
- [ ] `npm run e2e` passes: the queue shows 25 claims, all waiting, and clicking CLM-1001 opens `#/claims/CLM-1001`.
- [ ] `npm run e2e` passes twice in a row, and running it while `npm run dev` is up leaves the dev database unchanged (`GET http://localhost:8000/api/claims` is the same before and after).
- [ ] In the browser, with the Playwright MCP server at `http://localhost:5173`: the queue renders in dark and in light mode; the computed fonts are Geist for text and Geist Mono for ids and amounts; headings have weight 400; the page has no horizontal scroll at 1280 px wide. I take a screenshot of each mode.
- [ ] `npm run check:ts` passes: Prettier, ESLint, strict `tsc` with no `any`, and Vitest with coverage at 80% or more.

## Phase 5: The claim, the agent's work, sign-off and the instructions

**What it builds.**

- The claim view: its id, summary, status and amount claimed; a **Run the agent** button for a waiting claim; the decision with the outcome, the payout as the key figure, the reasons and the policy section; the payment, shown as paid, as waiting for sign-off or as not paid; a sign-off form for a claim waiting for sign-off, with a list of handlers and a **Sign off and pay** button; then the claim in full (the story, the items, each document) with the policy (plan, add-ons, trip dates, trip cost, travelers) and the customer's claim history.
- The agent's activity, next to the decision: each step in order, labeled as a tool call, a result, the reply or an error, with long results folded away. It refreshes every second while the claim is in progress.
- The instructions view: the agent's instructions as read-only text.

**Why now.** This is the screen the handlers work from, and it brings the whole pilot together: running the agent, following it step by step, reading its reasons and signing off.

**Success criteria**

- [ ] Vitest tests pass for the claim view (the decision, the payment states, the steps, the run button's request, and the sign-off request with the chosen handler) and for the instructions view.
- [ ] `npm run e2e` passes a test that plays the agent through the API, with no model: it starts CLM-1002 and posts steps, and the page shows them while the claim is in progress; it decides approve $1,150.00 and tries to pay, and the page shows "Waiting for sign-off" and no payment; it picks Dana Whitfield and signs off, and the page shows the claim decided and paid $1,150.00, signed off by Dana Whitfield.
- [ ] `npm run e2e` passes a test that the instructions view shows the instructions from the API and has no text field to edit them.
- [ ] In the browser, with the Playwright MCP server: the claim view for CLM-1001 renders in dark and light mode, every section is there, and the page has no horizontal scroll at 1280 px. I take a screenshot of each mode.
- [ ] `npm run check:ts` passes with coverage at 80% or more.

## Phase 6: The pilot end to end with the real agent

**What it builds.** No new features: this phase runs the whole pilot as a handler would, fixes whatever that turns up, and brings `docs/STATUS.md` up to date with what's built and how to run it.

**Success criteria**

- [ ] With `npm run dev` running, in the browser with the Playwright MCP server: on CLM-1001 I click **Run the agent**; the status goes to in progress, the steps appear one by one while the agent works, and then the decision appears with its reasons and policy section, and the payment if it approved.
- [ ] I run the agent the same way on CLM-1003 ($3,800 claimed) and CLM-1016 ($6,200 claimed). Where it approves more than $1,000, the claim waits for sign-off with nothing paid, the queue shows it in Alert, and signing off pays it.
- [ ] `docs/STATUS.md` describes what's built and how to run it: `npm run dev`, the dashboard's address, `uv run -m agent`, and `uv run -m backend.seed` to start over.
- [ ] `uv run -m backend.seed` leaves the dev database fresh for the student.
- [ ] `npm run check` passes in full: ruff, pyright, pytest, Prettier, ESLint, tsc, Vitest and Playwright.

## Not in this plan

- The claims manual, sign-in, real payments and messages to customers, as the spec sets out.
- Checking the agent's decisions against the handlers' decisions in `data/evals/`, which the spec keeps for later.
- `data/knowledge.json`, `data/policy_wording_short.md` and the security claim in `data/security/`, which the spec doesn't ask for.
- Anything from a later day's brief: the agent's harness, durable state, the swarm, versioned instructions, AWS.
