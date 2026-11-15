# Code standards

1. Keep it simple, do not overcomplicate.
2. Comments only when necessary.
3. Be concise: a short README and no emojis.
4. IMPORTANT: avoid overly defensive code. Handle exceptions only when necessary.
5. Use uv: ALWAYS `uv run`, NEVER `python3`.
6. TypeScript: strict mode, never `any`.

## Structure

7. Name each module for what it holds and keep one concern in it. A helper lives with its concern: never import a helper from a module about something else.
8. Each caller of the backend has one API client, `agent/api.py` and `dashboard/src/api.ts`, with one function for each operation, named for its operation id. Every path is written there and nowhere else.
9. Only `backend/agents.py` imports the agent, to start it.
10. Use the framework's own mechanism before you build one. In LangChain, a run's state reaches tools and middleware through `context_schema` and `ToolRuntime`, not through closures. Pass no setting that has no effect, such as a thread id without a checkpointer.

## The agent

11. `agent/harness.py` builds every agent: `create_agent`, the retries, the call limit and the agent's own middleware, and the stream. `agent/tools.py` holds every tool, at module level. `agent/claim.py` and `agent/queue.py` hold only UnderCover's rules. A new agent or tool fits this layout and never builds an agent of its own.
12. Write an agent's instructions as its goal, the rules that bind it and what a good result looks like, never as numbered steps. Leave out what the tools' descriptions say and what code enforces.
