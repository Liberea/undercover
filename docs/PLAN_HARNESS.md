# Plan: the agent's harness

This plan builds the brief in `docs/HARNESS.md` on top of the pilot in `docs/STATUS.md`. The UnderCover Agent becomes two agents. A **queue agent** works the whole queue from one run, plans it as a to-do list the dashboard shows, and hands each claim to a **claim agent** that starts clean, looks up the sections of the policy wording and the claims manual it needs, and reports back in one line. Failures are put right by code: retries, a failure count kept by the backend, and a check that nothing within the run's cap was missed.

It follows `docs/TECH_STACK.md`, `docs/CODE_STANDARDS.md`, `docs/PROCESS.md` and `docs/BRAND.md`. It adds no dependencies and no agent framework: both agents are LangChain's `create_agent`, and the middleware used comes with `langchain` 1.4, which is already installed.

## How it fits together

```
  Dashboard: queue page                      Backend: FastAPI + SQLite
  "Work the queue" (cap) --run_queue_agent-->  starts work_queue in the background
  polls get_latest_run and list_claims         keeps runs, to-do lists, failures

  +-------------------------------------------------------------------------+
  | Queue agent              create_agent, one per run                      |
  |   tools:      list_claims (waiting only), write_todos, work_claim       |
  |   middleware: model retry, model call limit, check for missed claims    |
  +------------------------------------+------------------------------------+
                                       | work_claim(claim_id)
                                       | one claim at a time, within the cap
                                       v
  +-------------------------------------------------------------------------+
  | Claim agent              create_agent, fresh messages for every claim   |
  |   tools:      get_claim, get_policy, get_claim_history,                 |
  |               list_sections, read_section, decide_claim, pay_claim      |
  |   middleware: model retry, model call limit                             |
  |   records every step on the claim, returns one line built from the     |
  |   claim's state: "CLM-1002: approved $1,150.00, waiting for sign-off"   |
  +-------------------------------------------------------------------------+
```

Everything still goes through the backend's API, and the backend still enforces the rules.

### The claim's states

A new state, **left for a handler**, holds a claim that failed twice.

```
 waiting --start_claim--> in progress --decide_claim--> decided
    ^                        |    \
    |                        |     `--decide_claim, approve over $1,000--> waiting for sign-off
    |                        |                                                    |
    `--release_claim---------+                                     sign_off_claim (pays)
       (first failure)       |                                                    v
                             |                                                 decided
                             `--release_claim (second failure)--> left for a handler
```

A claim fails when its run raises or ends without a decision. `release_claim` now counts failures: the first sends the claim back to waiting, the second leaves it for a handler. `start_claim` now starts only a waiting claim.

### The claim agent's one-line reports

| The claim after the run | The line |
|---|---|
| Approved and paid | `CLM-1001: approved $420.00, paid` |
| Approved over the limit | `CLM-1002: approved $1,150.00, waiting for sign-off` |
| Approved, payment refused or not made | `CLM-1001: approved $420.00, not paid` |
| Declined or referred | `CLM-1005: declined` / `CLM-1006: referred` |
| First failure | `CLM-1003: failed (The model is unavailable), back in the queue` |
| Second failure | `CLM-1003: failed twice (The model is unavailable), left for a handler` |
| Not waiting when asked | `CLM-1001: not started (Claim CLM-1001 is decided)` |

### The API

New, changed and removed operations. Every operation keeps an `operation_id`, a one-line docstring and only required inputs.

| `operation_id` | Route | Change | Used by |
|---|---|---|---|
| `list_sections` | `GET /api/documents/{document}/sections` | new | claim agent tool |
| `read_section` | `GET /api/documents/{document}/sections/{section}` | new | claim agent tool |
| `get_policy_wording` | `GET /api/policy-wording` | removed | (none) |
| `start_claim` | `POST /api/claims/{claim_id}/start` | only from waiting | claim agent's code |
| `release_claim` | `POST /api/claims/{claim_id}/release` | counts failures | claim agent's code |
| `get_instructions` | `GET /api/instructions` | returns `queue` and `claim` | both agents, dashboard |
| `create_run` | `POST /api/runs` | new | queue agent's code |
| `write_todos` | `PUT /api/runs/{run_id}/todos` | new | queue agent tool |
| `finish_run` | `POST /api/runs/{run_id}/finish` | new | queue agent's code |
| `get_latest_run` | `GET /api/runs/latest` | new | dashboard |
| `run_queue_agent` | `POST /api/queue/agent-runs` | new | dashboard |

`{document}` is `policy_wording` or `claims_manual`. A run has an id, a cap, a status (running or finished), its to-do list, the summary, and when it started and finished. A to-do item has a text and a status: `to_do`, `in_progress`, `done` or `left_for_handler`.

### The middleware

| Middleware | Queue agent | Claim agent | What it handles |
|---|---|---|---|
| `ModelRetryMiddleware`: 2 retries with backoff, then raise | yes | yes | Errors from the model provider and timeouts (the model also gets a 60-second request timeout) |
| `ModelCallLimitMiddleware`: raise at the limit | 4 x cap + 10 calls | 25 calls | An agent that goes round in circles and runs up cost |
| Check for missed claims: our own `after_model` hook | yes | no | Finishing while a claim within the cap is still waiting |

### Key choices and why

1. **Two `create_agent` agents, no new framework.** The brief asks for these pieces in our own agent. A subagent is a tool, `work_claim`, that runs the claim agent with fresh messages and returns one line. This is what Deep Agents' `task` tool did in Lab 2, in about twenty lines of our own code. The claim agent is the pilot's agent with new tools and middleware.
2. **The report line comes from the claim's state, not from the claim agent's reply.** After a claim's run, `work_claim` reads the claim from the API and writes the line (table above). The queue agent sees what the backend holds and nothing else, and its context grows by one short line per claim, not by the claim's whole conversation.
3. **The cap is enforced in code.** `work_claim` keeps the set of claims the run has taken. Once that set holds `cap` claims, it refuses any new claim ("This run's cap of 5 claims is reached"), but it still accepts a retry of a claim already in the set. I checked with a stub model that LangGraph runs parallel tool calls at the same time, in threads. So `work_claim` holds a lock and works one claim at a time, and the cap check sits inside that lock.
4. **The backend counts failures and refuses double work.** `release_claim` counts each failure, and the second one leaves the claim for a handler. `start_claim` now starts only a waiting claim, so two runs can't work the same claim. These two changes, with the refusals the pilot already has (deciding a claim that isn't in progress, paying twice), keep any claim from being decided or paid twice, whatever the agents do. This is the same principle as the sign-off limit.
5. **The claim agent never raises.** `run(claim_id, thread_id)` catches every failure in one place: the provider, a timeout, the call limit or a tool. It records the failure as an error step, releases the claim and returns the report line. If an exception got out of a tool, it would end the queue agent's whole run (pilot key choice 3), so this one `try` is how one bad claim never stops the run.
6. **Model calls are retried. Tool calls are not.** A failed model call has no side effects, so `ModelRetryMiddleware` retries it. `decide_claim` and `pay_claim` do have side effects. The retry for a claim is its second attempt, from a clean start, later in the run.
7. **The check for missed claims is middleware, not only an instruction.** When the queue agent answers without a tool call, it wants to finish. At that point an `after_model` hook reads the waiting claims. The hook looks for a claim of this run that is waiting again, or, if the run is below its cap, any waiting claim. If it finds one, it adds a message that names the claims and sends the agent back to the model (`jump_to: "model"`). I checked this with a stub model. The loop ends: each claim fails at most twice, and the cap limits how many new claims the run takes. The instructions also ask the agent to check, and the hook makes the check certain.
8. **Our own `write_todos`, stored by the backend.** LangChain's `TodoListMiddleware` keeps the list in the agent's state and has only three statuses: pending, in progress and completed. The brief needs a fourth, left for a handler, and the dashboard needs to read the list. So our `write_todos` tool replaces the run's whole list through the API. It works like Deep Agents' tool of the same name and uses our four statuses.
9. **The agent looks up sections. It doesn't get whole documents.** `list_sections` returns a document's contents, which list each numbered section with the bold topics inside it, such as `7. Interpretation notes: Unattended belongings, Vehicles, ..., Wild animals, ...`. The topics matter: the manual's rule on wild animals is inside section 7, and a list of section titles alone would not show it. `read_section` returns one section. It also passes a short label, such as `Claims manual, 7. Interpretation notes`, as the tool's artifact. When a read is refused, there is no label. I checked that the artifact reaches the stream. The agent records each successful read as a `read` step, and the claim page lists them as the sections the agent read.
10. **The step recorder reads only the model and tool updates.** With middleware, the stream also yields updates from the middleware's own nodes, such as `{'ModelCallLimitMiddleware.before_model': None}` (checked). The pilot's recorder reads `node["messages"]` from every update, so it would fail on these.
11. **Runs start like claim runs.** `run_queue_agent(cap)` gives the run a new id and starts `work_queue(run_id, cap)` in a FastAPI background task, as `run_agent` does for one claim. The command line starts runs in the same way. There is no lock on runs: if a process stops partway, a lock could be left in place, and `start_claim` already keeps two runs off the same claim.
12. **Two sets of instructions.** `backend/instructions/queue.md` covers running the queue, and `backend/instructions/claim.md` covers working one claim. `get_instructions` serves both, and the instructions page shows both. The claim instructions follow section 4 of the manual, "Working a claim", and say where to look things up. They come from the wording and the manual only. `data/evals/` is never opened.
13. **DeepSeek V4.1 Flash by default.** `deepseek/deepseek-v4.1-flash` with low reasoning effort, as in Lab 2. `MODEL_NAME` still overrides it.

## Phase 1: Looking up the wording and the manual, on the new model

**What it builds.**

- `backend/documents.py`: `list_sections` and `read_section` for `policy_wording` and `claims_manual`. They split each document at its `## ` headings and take the topics from the bold words that open a paragraph. They return 404 for an unknown document or section. `get_policy_wording` is removed.
- `agent/tools.py`: `list_sections(document)` and `read_section(document, section)` replace `get_policy_wording`. The model passes a document name and a section number. These are shared, read-only documents, so a name and a number can't steer the agent to a customer's records.
- A new step kind, `read`. Its first line names the section and the section's text follows. The kind is added in the backend, in the agent's step recorder and in the dashboard.
- The claim page's activity: `read` steps are labeled "Read", their text is folded away like a result, and the top of the card lists the sections the agent read.
- `backend/instructions.md` is rewritten from the wording and the manual: work the claim in the order of manual section 4, look up the contents of both documents, read the benefit's section, the exclusions, the payment rules and the manual sections that bear on the claim, then decide, record the decision and pay as before.
- The default model becomes DeepSeek V4.1 Flash with low reasoning effort.
- `docs/SPEC.md`: the claims manual comes out of "Not for now". The agent reads the sections of the wording and the manual that it needs. Decisions follow the wording first and then the manual.

**Why first.** The claim agent is what the queue agent will hand claims to, so it is built first. On a single claim it can be tested and tried with the real model for a cent.

**Success criteria**

- [x] `uv run pytest backend` passes, with tests that `list_sections` returns the wording's 12 sections and the manual's 14, each with its number and title, that the manual's section 7 has the topic "Wild animals", that `read_section` returns the manual's section 9 with its title "Repeat claims" and its text, and that an unknown document and an unknown section each give 404.
- [x] The OpenAPI test still passes: every operation has an `operation_id`, a one-line description and no optional inputs. `GET /api/policy-wording` gives 404.
- [x] `uv run pytest agent` passes, with a stub model, for a run that calls `list_sections` and `read_section`. The steps include a `read` step whose first line is `Claims manual, 7. Interpretation notes`. A refused read (section 99) records a result and no `read` step.
- [x] A test checks the model's tools: `get_claim`, `get_policy`, `get_claim_history`, `list_sections`, `read_section`, `decide_claim` and `pay_claim`. `get_policy_wording` is gone, and the names still match operation ids.
- [x] The model test passes: `deepseek/deepseek-v4.1-flash` with low reasoning by default, and `MODEL_NAME` when it's set.
- [x] `git grep --untracked -n "evals" -- backend agent` finds nothing.
- [x] Vitest passes for the activity: `read` steps are labeled "Read", and the list of sections read is shown.
- [x] One real run with `MODEL_NAME` unset and the backend running. After `uv run -m backend.seed`, `uv run -m agent CLM-1020` (sunglasses taken by a monkey) prints a reply. Its steps include `list_sections` and a `read` step for `Claims manual, 7. Interpretation notes`, and the claim has a decision with reasons and a policy section. This costs about a cent. Then `uv run -m backend.seed`.
- [x] In the browser with the Playwright MCP server, the claim page for CLM-1020 lists the sections the agent read, in dark and in light mode. I take a screenshot of each mode.
- [x] `npm run check:python` and `npm run check:ts` pass with coverage at 80% or more.

## Phase 2: Putting problems right on a claim

**What it builds.**

- Backend: a `failures` count on each claim, starting at 0. `release_claim` adds one and then sends the claim to `waiting`, or to `left_for_handler` on the second failure. `start_claim` refuses a claim that isn't waiting (409).
- `agent/main.py` becomes `agent/claim.py`, the claim agent. `model()` moves to `agent/model.py`, together with the middleware both agents share: `ModelRetryMiddleware` (2 retries, then raise) and a 60-second request timeout. The claim agent also gets `ModelCallLimitMiddleware` with a limit of 25 model calls.
- `run(claim_id, thread_id)` never raises and returns the report line. Every failure becomes an error step and a release. A run that ends without a decision counts as a failure.
- The step recorder reads only the `model` and `tools` updates.
- `backend/runs.py` starts `agent.claim.run`. `uv run -m agent CLM-1001` prints the report line, and `uv run -m agent` goes on to the next claim when one fails. Phase 3 replaces this loop with the queue agent.
- Dashboard: the status "Left for a handler" in Alert, since it needs a handler, in the queue's counts and on the claim page. Like any status other than waiting, it has no Run the agent button.

**Why now.** The queue agent can only be trusted with many claims once one claim can fail without harm. Building this into the claim agent and the backend first keeps the queue agent simple.

**Success criteria**

- [x] Backend tests: a claim released once is `waiting`. Released a second time, it is `left_for_handler`. `start_claim` on a claim in progress, decided or left for a handler gives 409. Deciding a decided claim and paying twice still give 409.
- [x] Agent tests with stub models:
  - [x] A model that fails once and then works: the retry carries the run through, and the claim is decided.
  - [x] A model that always fails: `run` returns `CLM-1001: failed (The model is unavailable), back in the queue` without raising. The claim is waiting, and the error is a step. A second such run returns the "failed twice" line, and the claim is `left_for_handler`.
  - [x] A model that keeps calling tools without deciding is stopped by the call limit, and the run counts as a failure.
  - [x] A run that ends without a decision counts as a failure.
  - [x] The report lines for approved and paid, waiting for sign-off, declined and referred.
  - [x] `run` on a decided claim returns `not started (...)` and changes nothing.
- [x] Vitest passes for the new status's label and pill and for the queue's counts.
- [x] `npm run e2e` passes a test that releases a claim twice through the API. The queue and the claim page show it as "Left for a handler", and the claim page has no Run the agent button.
- [x] `npm run check:python` and `npm run check:ts` pass with coverage at 80% or more.

## Phase 3: The queue agent and its runs

**What it builds.**

- Backend: a `runs` table and the operations `create_run`, `write_todos`, `finish_run`, `get_latest_run` and `run_queue_agent`, in `backend/queue.py`.
- The instructions are split into `backend/instructions/queue.md` and `backend/instructions/claim.md`. `get_instructions` returns both, and the instructions page shows them under "Working the queue" and "Working a claim".
- `agent/queue.py`: `work_queue(run_id, cap)` creates the run and builds the queue agent with three tools: `list_claims` (the waiting claims, with id, type, amount and date submitted), `write_todos` and `work_claim`. It adds the middleware from the table, including the check for missed claims. It streams the run and finishes it with the agent's final reply as the summary. If the queue agent itself fails, the run is finished with "The run stopped: ..." and the error is raised.
- The queue instructions tell the agent to: list the waiting claims, write a to-do list with one item for each claim it will take within the cap plus a last item for the summary, choose the order and say why, mark each item as it goes, try a claim that comes back to the queue again later in the run, list the waiting claims again before finishing, and end with a short summary for the handlers (what was decided, what waits for sign-off and what is left for a handler, and why).
- The command line: `uv run -m agent` works the whole queue, `uv run -m agent --cap 5` caps the run at five claims, and `uv run -m agent CLM-1001` works one named claim with the claim agent. It prints each claim's line as it comes in, and then the summary.

**Why now.** With a claim agent that never stops the run, the queue agent is just planning, handing off and checking. Its tests can cover every failure path with stub models.

**Success criteria**

- [x] Backend tests: create a run. `write_todos` replaces its list. An unknown to-do status gives 422. `finish_run` stores the summary and marks the run finished. `get_latest_run` returns the newest run, or 404 when there is none. `run_queue_agent` returns 202 with a run id and starts the run with the cap (the run is replaced by a stub).
- [x] Agent tests, with stub models for both agents:
  - [x] **The to-do list is stored:** the stub writes a list and then updates it, and `get_latest_run` shows each version, then the summary.
  - [x] **The cap:** with a cap of 2 and a stub that asks for three claims, two are worked. The third gets the cap refusal and stays waiting, like the other claims.
  - [x] **A failed claim doesn't stop the run:** the claim agent fails on the first claim, and the run goes on and finishes with a summary.
  - [x] **A failed claim goes back in the queue and is tried again:** a claim fails once and is decided on its second try in the same run.
  - [x] **A claim that fails twice is left for a handler:** the run finishes and doesn't try it a third time.
  - [x] **The check for missed claims:** the stub tries to finish with a waiting claim inside its cap. The hook's message names that claim, the stub works it, and then the run finishes. At the cap, the stub finishes with no message from the hook.
  - [x] **Nothing is decided twice:** asked to work a decided claim, `work_claim` reports `not started` and the decision stays as it was.
  - [x] The queue agent's system prompt is the queue instructions, and the claim agent's is the claim instructions, both from the API.
  - [x] The command line: `--cap`, one named claim, and the whole queue.
- [x] Vitest and `npm run e2e` pass for the instructions page showing both sets of instructions, read only.
- [x] One real run with `MODEL_NAME` unset and the backend running. After `uv run -m backend.seed`, `uv run -m agent --cap 5` prints five claims' lines and a summary. `GET /api/runs/latest` shows the run finished, with every to-do item done or left for a handler, and with the summary. `GET /api/claims` shows 20 claims still waiting. This costs a few cents. Then `uv run -m backend.seed`.
- [x] `npm run check:python` and `npm run check:ts` pass with coverage at 80% or more.

## Phase 4: The run on the dashboard

**What it builds.**

- `dashboard/src/api.ts`: the `Run` and `Todo` types, `getLatestRun` and `runQueueAgent`.
- On the queue page, a card for the current run, polled every two seconds with the claims. It shows when the run started, its cap, whether it is running or finished, the to-do list with each item's status, and the summary once the run has finished. Before the first run it says "No run yet." The statuses use the brand order: to do warm, in progress mid, done cool, and left for a handler in Alert.
- A **Work the queue** form next to it: a number field, "Claims", from 1 to the number waiting and 5 by default, and the primary button. The button is disabled while the request is sent, and an error is shown if it fails.

**Why now.** With the run and its to-do list in the backend, the dashboard can show them. The end-to-end test plays the queue agent's part through the API, so it never calls a model.

**Success criteria**

- [ ] Vitest passes for the run card (items and status labels from a stubbed API, the summary once finished, and "No run yet.") and for the Work the queue request with the number chosen.
- [ ] `npm run e2e` passes a test that plays a run through the API. It creates a run with a cap of 2 and writes two items to do, and the page shows them. It marks one in progress and then done, and the page follows. It finishes the run with a summary, and the page shows "Finished" and the summary.
- [ ] In the browser with the Playwright MCP server, the queue page with the run card renders in dark and in light mode, with no horizontal scroll at 1280 px. I take a screenshot of each mode.
- [ ] `npm run check:ts` passes with coverage at 80% or more.

## Phase 5: The harness end to end with the real model

**What it builds.** No new features. This phase runs the harness the way the brief's "What done looks like" describes, fixes whatever that turns up, and brings the documents up to date.

**Success criteria**

- [ ] With `MODEL_NAME` unset, after `uv run -m backend.seed`, and with `npm run dev` running, in the browser with the Playwright MCP server: on the queue page I work the queue with 5 claims. The run card shows the to-do list filling in and being ticked off. Five claims move through in progress to decided or waiting for sign-off (or left for a handler), and 20 stay waiting. The summary appears when the run finishes.
- [ ] On a claim the run worked, the claim page shows its steps and the sections the agent read. Where it approved more than $1,000, the claim waits for sign-off and nothing has been paid.
- [ ] `docs/SPEC.md`, `docs/TECH_STACK.md` and `docs/STATUS.md` describe the product as it now is: the queue agent and the claim agent, the model, the run and its to-do list, the new state, and how to run it (`--cap`, a named claim, Work the queue).
- [ ] `uv run -m backend.seed` leaves the dev database fresh for the student.
- [ ] `npm run check` passes in full: ruff, pyright, pytest, Prettier, ESLint, tsc, Vitest and Playwright.

## Not in this plan

- A claim left in progress when the process itself dies partway, for example when the backend restarts during a run. The harness handles failures inside a run. Recovering from a lost process needs durable state, which comes on a later day.
- What a handler does with a claim left for a handler, such as putting it back in the queue or deciding it by hand. The brief doesn't ask for it.
- Working claims in parallel. One claim at a time keeps the cap simple and the run cheap to watch.
- Summarizing a long conversation. Each claim starts clean, and the queue agent's context grows by one line per claim.
- Checking decisions against the handlers' decisions in `data/evals/`.
- Anything from a later day's brief: durable state, the swarm, versioned instructions, sign-in, AWS.
