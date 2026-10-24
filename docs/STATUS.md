# Status

The claims pilot from `docs/PLAN.md` is built: all six phases are done.

## Built

- `backend/`: FastAPI on SQLite. On first start it builds `backend/undercover.db` from `data/` (never `data/evals/`); `UNDERCOVER_DB` points it at another file.
  - Read operations: `list_claims`, `get_claim`, `get_policy`, `get_claim_history` (no contact details), `get_policy_wording`, `list_handlers`, `get_instructions`, `health`.
  - A claim's states: waiting, in progress, waiting for sign-off, decided. `start_claim`, `release_claim`, `decide_claim`, `pay_claim` and `sign_off_claim` move it between them.
  - `pay_claim` refuses a payout over $1,000.00 (403) until a handler signs off; `sign_off_claim` then pays it. The limit comes from `data/company.json`.
  - `add_step` and `list_steps` hold what the agent did on a claim; `run_agent` starts the agent on a waiting claim in the background.
  - The agent's instructions are `backend/instructions.md`.
- `agent/`: the UnderCover Agent, `run(claim_id, thread_id)`, on `create_agent` with GPT-6 Luna (low reasoning) or the model in `MODEL_NAME`. Its six tools (`agent/tools.py`) each call one API operation, are bound to the run's claim so the model passes no ids, and hand the backend's refusals back to the model as text. It records every step through the API, and a run that fails or ends without a decision puts the claim back in the queue.
- `dashboard/`: React and Vite in the brand's look, dark by default with a light mode switch.
  - The claims queue shows how many claims are in each state and every claim with its status and decision, refreshed every two seconds.
  - A claim's page shows the claim in full with its policy and the customer's earlier claims, a Run the agent button while it waits, the decision with its reasons, policy section and payment, a sign-off form for a payout over $1,000, and the agent's steps, refreshed every second.
  - The instructions page shows the agent's instructions, read only.
- `e2e/`: Playwright tests of the queue, a claim and the instructions. They start their own backend on port 8100 with a fresh database (`e2e/e2e.db`) and their own dashboard on port 5180, so they never touch the dev data. The claim test plays the agent through the API, since tests never call a model.

## Run it

- `npm run dev` starts the backend on port 8000 and the dashboard at http://localhost:5173. Open a claim and press Run the agent.
- `uv run -m agent CLM-1001` runs the agent on one claim from the command line; `uv run -m agent` works through every waiting claim. The backend must be running.
- `uv run -m backend.seed` rebuilds the database from `data/`, putting every claim back to waiting.
- `npm run check` runs every check.

The dev backend reloads when `backend/` changes. After a change in `agent/`, restart `npm run dev` so that Run the agent uses the new code.

## Known limits

- Now and then the model gives its decision in its reply without calling `decide_claim` (1 run in 4 while building phase 3, none in the runs after). The run then puts the claim back in the queue and says so in its steps.
- There is no sign-in, as the spec asks, so anyone using the API can sign off as any handler. The agent has no tool to sign off.
