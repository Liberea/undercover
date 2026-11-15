# Status

The claims pilot from `docs/PLAN.md` is built: all six phases are done. The harness from `docs/PLAN_HARNESS.md` is being built: phases 1 and 2 are done.

## Built

- `backend/`: FastAPI on SQLite. On first start it builds `backend/undercover.db` from `data/` (never `data/evals/`); `UNDERCOVER_DB` points it at another file.
  - Read operations: `list_claims`, `get_claim`, `get_policy`, `get_claim_history` (no contact details), `list_handlers`, `get_instructions`, `health`.
  - `list_sections` and `read_section` serve the policy wording and the claims manual section by section: the contents list each numbered section with the bold topics inside it. Neither document is served whole.
  - A claim's states: waiting, in progress, waiting for sign-off, decided, left for a handler. `start_claim`, `release_claim`, `decide_claim`, `pay_claim` and `sign_off_claim` move it between them.
  - `start_claim` starts only a waiting claim. `release_claim` counts a failed run: the first sends the claim back to waiting, the second leaves it for a handler.
  - `pay_claim` refuses a payout over $1,000.00 (403) until a handler signs off; `sign_off_claim` then pays it. The limit comes from `data/company.json`.
  - `add_step` and `list_steps` hold what the agent did on a claim; `run_agent` starts the agent on a waiting claim in the background.
  - The agent's instructions are `backend/instructions.md`.
- `agent/`: the UnderCover Agent. `agent/claim.py` has `run(claim_id, thread_id)`, which works one claim on `create_agent` with the model from `agent/model.py`: DeepSeek V4.1 Flash (low reasoning, 60-second timeout) or the model in `MODEL_NAME`. Its seven tools (`agent/tools.py`) each call one API operation, are bound to the run's claim so the model passes no record ids, and hand the backend's refusals back to the model as text. It looks up the sections of the wording and the manual it needs with `list_sections` and `read_section`, and each section it reads is recorded as a `read` step. It records every step through the API. `ModelRetryMiddleware` retries a failed model call twice, and `ModelCallLimitMiddleware` stops a run after 25 model calls. `run` never raises: a run that fails or ends without a decision is recorded as an error step and released, and `run` returns one line, such as `CLM-1002: approved $1,150.00, waiting for sign-off` or `CLM-1003: failed (...), back in the queue`.
- `dashboard/`: React and Vite in the brand's look, dark by default with a light mode switch.
  - The claims queue shows how many claims are in each state and every claim with its status and decision, refreshed every two seconds.
  - A claim's page shows the claim in full with its policy and the customer's earlier claims, a Run the agent button while it waits, the decision with its reasons, policy section and payment, a sign-off form for a payout over $1,000, and the agent's steps with the sections it read, refreshed every second.
  - The instructions page shows the agent's instructions, read only.
- `e2e/`: Playwright tests of the queue, a claim and the instructions. They start their own backend on port 8100 with a fresh database (`e2e/e2e.db`) and their own dashboard on port 5180, so they never touch the dev data. The claim test plays the agent through the API, since tests never call a model.

## Run it

- `npm run dev` starts the backend on port 8000 and the dashboard at http://localhost:5173. Open a claim and press Run the agent.
- `uv run -m agent CLM-1001` runs the agent on one claim from the command line and prints its one-line report; `uv run -m agent` works through every waiting claim. The backend must be running.
- `uv run -m backend.seed` rebuilds the database from `data/`, putting every claim back to waiting. Run it after pulling a change to the database's tables, such as the claims' failure count.
- `npm run check` runs every check.

The dev backend reloads when `backend/` changes. After a change in `agent/`, restart `npm run dev` so that Run the agent uses the new code.

## Known limits

- Now and then the model gives its decision in its reply without calling `decide_claim` (1 run in 4 while building phase 3, none in the runs after). The run counts that as a failure, puts the claim back in the queue and says so in its steps.
- There is no sign-in, as the spec asks, so anyone using the API can sign off as any handler. The agent has no tool to sign off.
