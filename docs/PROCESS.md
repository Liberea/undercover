# Process

`uv sync` and `npm install` at the repo root install everything, including a git pre-commit hook. `npm run dev` starts the backend and the dashboard.

`npm run check` runs every check:

- Python: ruff (lint and format), pyright, and pytest with 80% coverage
- TypeScript: ESLint, Prettier, tsc, and vitest with 80% coverage
- Playwright end-to-end tests

The pre-commit hook runs the format, lint, type and unit test checks on every commit.

## Planning

When asked to plan, as in "Please plan the pilot", write the plan to `docs/PLAN.md` and write no code.

- Split the work into phases, usually 5 or 6, each building on the last.
- Give each phase detailed success criteria that you can verify yourself: tests that pass, commands and their output, API calls and their responses, and pages you check in the browser with the Playwright MCP server. Write each one as a checkbox.
- Say where each phase's code goes: the modules it adds or changes, and why, as `docs/CODE_STANDARDS.md` asks. Give each phase a criterion for its structure as well as its behavior.
- When the work would build on code that doesn't meet the standards, plan putting that code right as a step of its own, before the new work and with its behavior unchanged.
- Then stop and wait until you are asked to implement the plan.

## Implementing

When asked to implement the plan, as in "Please implement the plan for the pilot", build every phase in order without stopping. For each phase:

1. Build it, with tests.
2. Check every success criterion and fix whatever fails.
3. Review the phase's diff against `docs/CODE_STANDARDS.md` and fix what the review finds: where each new piece lives, anything written a second time (a path, a helper, an agent's setup), closures or settings where the framework has a mechanism, and instructions written as steps. A green `npm run check` proves the behavior, not the structure.
4. Tick off its criteria in `docs/PLAN.md` and update `docs/STATUS.md`.
5. Commit. The pre-commit hook runs the checks; if it fails, fix the problem and commit again.

When the last phase is done, run `npm run check` and report the results.

## Rules

- Add tests with each change. Tests never call a model; use a stub model.
- Code from an earlier build meets the standards too. When you build on a shortcut, put it right first; never copy it.
- Outside a plan, commit each change once you have checked it.
- Run `npm run check` before you hand work over.
- Never use `git commit --no-verify`.
- Never lower a threshold, turn off a rule or exclude a file to get a green run. If a rule looks wrong, stop and ask.
- Keep `docs/STATUS.md` up to date.
- Never push.
- Don't open `data/evals/` unless you're asked to.
- Everything must work on Windows: write `package.json` scripts as `uv run` commands or `.mjs` files.
