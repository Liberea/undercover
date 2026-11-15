# Status

The claims pilot from `docs/PLAN.md` is built: all six phases are done. The harness from `docs/PLAN_HARNESS.md` is built: all five phases are done. The review in `docs/HUMAN_REVIEW_HARNESS.md` is answered: the agent has one API client, its harness is separate from UnderCover's rules, its tools read the run's context, the backend's modules are named for what they hold, and the instructions give goals rather than steps. The behavior, the API and the report lines are the same, and `docs/CODE_STANDARDS.md` and `docs/PROCESS.md` now ask for this structure and a review of it in each phase.

## Built

- `backend/`: FastAPI on SQLite. On first start it builds `backend/undercover.db` from `data/` (never `data/evals/`); `UNDERCOVER_DB` points it at another file.
  - Read operations: `list_claims`, `get_claim`, `get_policy`, `get_claim_history` (no contact details), `list_handlers`, `get_instructions`, `health`.
  - `list_sections` and `read_section` serve the policy wording and the claims manual section by section: the contents list each numbered section with the bold topics inside it. Neither document is served whole.
  - A claim's states: waiting, in progress, waiting for sign-off, decided, left for a handler. `start_claim`, `release_claim`, `decide_claim`, `pay_claim` and `sign_off_claim` move it between them.
  - `start_claim` starts only a waiting claim. `release_claim` counts a failed run: the first sends the claim back to waiting, the second leaves it for a handler.
  - `pay_claim` refuses a payout over $1,000.00 (403) until a handler signs off; `sign_off_claim` then pays it. The limit comes from `data/company.json`.
  - `backend/steps.py` has `add_step` and `list_steps`, which hold what the agent did on a claim.
  - `backend/runs.py` has the queue agent's runs. A run has a cap, a status (running or finished), a to-do list and a summary: `create_run`, `write_todos`, `finish_run` and `get_latest_run` (null before the first run).
  - `backend/agents.py` is the one backend module that imports the agent. `run_agent` starts the claim agent on a waiting claim in the background, and `run_queue_agent` starts a run of the queue agent. `get_instructions` serves the agent's instructions, `backend/instructions/queue.md` for working the queue and `backend/instructions/claim.md` for working a claim. Each instruction gives the goal, the rules that bind the agent and what a good result looks like.
- `agent/`: the UnderCover Agent, as two agents.
  - `agent/api.py` is the agent's client for the backend: one function for each of the 15 operations it uses, with every path in this module. The caller says what a refusal means: `result()` stops the run, `tool_reply()` hands it to the model.
  - `agent/harness.py` builds both agents on `create_agent` with the model from `agent/model.py`: DeepSeek V4.1 Flash (low reasoning, 60-second timeout) or the model in `MODEL_NAME`. `ModelRetryMiddleware` retries a failed model call twice, `ModelCallLimitMiddleware` stops an agent at its call limit, and an agent can add middleware of its own. `stream()` gives the run's context to the tools and middleware through `context_schema`, and yields each message from the model and the tools.
  - `agent/tools.py` holds all ten tools at module level. The claim agent's seven each call one API operation, read the claim from the run's `ClaimContext` through `ToolRuntime`, so the model passes no record ids, and hand the backend's refusals back to the model as text. The queue agent's are `list_claims` (the waiting claims), `write_todos` and `work_claim`, which hands one claim to a claim agent and returns its one-line report.
  - `agent/queue.py` has `work_queue(run_id, cap)`, the queue agent, and the queue's rules. Its context, `queue.Run`, works one claim at a time and refuses a new claim once the run holds `cap` claims. A hook after each model call sends the agent back when it tries to finish with a waiting claim missed within its cap, and the agent may make 4 x cap + 10 model calls. It finishes the run with its summary, or with the error if it fails itself.
  - `agent/claim.py` has `run(claim_id, thread_id)`, the claim agent, and the claim's rules. The agent looks up the sections of the wording and the manual it needs with `list_sections` and `read_section`, and each section it reads is recorded as a `read` step. It records every step through the API and may make 25 model calls. `run` never raises: a run that fails or ends without a decision is recorded as an error step and released, and `run` returns one line, such as `CLM-1002: approved $1,150.00, waiting for sign-off` or `CLM-1003: failed (...), back in the queue`.
- `dashboard/`: React and Vite in the brand's look, dark by default with a light mode switch.
  - The claims queue shows how many claims are in each state and every claim with its status and decision, refreshed every two seconds.
  - Above the claims, the agent's latest run shows whether it is running or finished, its cap, its to-do list with each item's status, and the summary once it has finished. The Work the queue form starts a run on 1 to all the waiting claims, 5 by default.
  - A claim's page shows the claim in full with its policy and the customer's earlier claims, a Run the agent button while it waits, the decision with its reasons, policy section and payment, a sign-off form for a payout over $1,000, and the agent's steps with the sections it read, refreshed every second.
  - The instructions page shows the agent's instructions for working the queue and for working a claim, read only.
- `e2e/`: Playwright tests of the queue, a claim, a claim left for a handler, the agent's run and the instructions. They start their own backend on port 8100 with a fresh database (`e2e/e2e.db`) and their own dashboard on port 5180, so they never touch the dev data. The claim and run tests play the agents through the API, since tests never call a model.

## Run it

- `npm run dev` starts the backend on port 8000 and the dashboard at http://localhost:5173. On the queue page, choose a number of claims and press Work the queue, or open a claim and press Run the agent.
- `uv run -m agent --cap 5` runs the queue agent on at most five waiting claims, printing each claim's report and then the summary; `uv run -m agent` works the whole queue; `uv run -m agent CLM-1001` works one claim. The backend must be running.
- `uv run -m backend.seed` rebuilds the database from `data/`, putting every claim back to waiting. Run it after pulling a change to the database's tables, such as the claims' failure count or the runs.
- `npm run check` runs every check.

The dev backend reloads when `backend/` changes. After a change in `agent/`, restart `npm run dev` so that Run the agent uses the new code.

## Known limits

- Now and then the model gives its decision in its reply without calling `decide_claim` (1 run in 4 while building the pilot's phase 3, none in the runs after). The run counts that as a failure, puts the claim back in the queue and says so in its steps.
- There is no sign-in, as the spec asks, so anyone using the API can sign off as any handler or start a run. The agent has no tool to sign off.
- The run's summary is the queue agent's own prose. In the first live run it said older claims had been left behind when it had in fact taken the oldest first. The queue instructions now ask it to take every fact from the claim agents' reports, and in the run after the review every fact in the summary was right. The claims' states and the one-line reports, which code builds from the backend, are the record.
- The claim agent reads widely, which costs tokens: 11 to 13 of the 26 sections on each claim with the step-by-step instructions, and 12 to 17 with the goal-based ones. The five claims in the run after the review got the same outcomes and payouts as before it. Its decisions have not been checked against `data/evals/` yet.
- If the process running the agent dies partway, for example when the dev backend reloads during a run, the claim it was working stays in progress and the run stays running. `uv run -m backend.seed` clears both. Recovering from that needs durable state, which comes on a later day.
- Nothing stops two runs at once. `start_claim` keeps them off the same claim, so no claim is worked twice.
