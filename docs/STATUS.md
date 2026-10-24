# Status

The claims pilot is being built from `docs/PLAN.md`. Done so far: phase 1.

## Built

- `backend/`: FastAPI on SQLite. On first start it builds `backend/undercover.db` from `data/` (never `data/evals/`); `UNDERCOVER_DB` points it at another file. Read operations: `list_claims`, `get_claim`, `get_policy`, `get_claim_history` (no contact details), `get_policy_wording`, `list_handlers`, `health`.
- `agent/`: still the skeleton, `run(claim_id, thread_id)` with one tool that calls the health route.
- `dashboard/`: still the skeleton page that shows whether the backend is up.
- `e2e/`: one test of that page.

## Run it

- `npm run dev` starts the backend on port 8000 and the dashboard on port 5173.
- `uv run -m backend.seed` rebuilds the database from `data/`, putting every claim back to waiting.
- `npm run check` runs every check.
