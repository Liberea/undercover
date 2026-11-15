import { useState } from "react";
import {
  getLatestRun,
  message,
  runQueueAgent,
  type Run,
  type TodoStatus,
} from "./api";
import { moment } from "./format";
import { usePolling } from "./hooks";

const TODO_LABELS: Record<TodoStatus, string> = {
  to_do: "To do",
  in_progress: "In progress",
  done: "Done",
  left_for_handler: "Left for a handler",
};

const DEFAULT_CAP = 5;

export function QueueRun({ waiting }: Readonly<{ waiting: number }>) {
  const { data: run } = usePolling(getLatestRun, 2000);
  return (
    <section className="card section queue-run" aria-label="The agent's run">
      <div className="run-head">
        <h2>The agent&apos;s run</h2>
        <WorkTheQueue waiting={waiting} />
      </div>
      {run === null && <p className="muted">No run yet.</p>}
      {run && <RunDetails run={run} />}
    </section>
  );
}

function RunDetails({ run }: Readonly<{ run: Run }>) {
  const running = run.status === "running";
  return (
    <>
      <p className="muted">
        <span className={running ? "run-running" : "run-finished"}>
          {running ? "Running" : "Finished"}
        </span>
        , started {moment(run.started_at)}, up to {run.cap} claims
      </p>
      {run.todos.length > 0 && (
        <ol className="todos" aria-label="The agent's to-do list">
          {run.todos.map((todo, index) => (
            <li key={index}>
              <span className={`pill todo-${todo.status}`}>
                <span className="dot" aria-hidden="true" />
                {TODO_LABELS[todo.status]}
              </span>
              <span>{todo.content}</span>
            </li>
          ))}
        </ol>
      )}
      {run.summary && (
        <div className="run-summary">
          <h3>Summary for the handlers</h3>
          <p>{run.summary}</p>
        </div>
      )}
    </>
  );
}

function WorkTheQueue({ waiting }: Readonly<{ waiting: number }>) {
  const [cap, setCap] = useState(String(DEFAULT_CAP));
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string>();
  const claims = Number(cap);
  const valid = Number.isInteger(claims) && claims >= 1 && claims <= waiting;
  const start = () => {
    setSending(true);
    setError(undefined);
    runQueueAgent(claims)
      .catch((failure: unknown) => {
        setError(message(failure));
      })
      .finally(() => {
        setSending(false);
      });
  };
  return (
    <form
      className="work-queue"
      onSubmit={(event) => {
        event.preventDefault();
        start();
      }}
    >
      <label>
        Claims
        <input
          type="number"
          min={1}
          max={waiting}
          value={cap}
          onChange={(event) => {
            setCap(event.target.value);
          }}
        />
      </label>
      <button
        type="submit"
        className="button button-primary"
        disabled={!valid || sending}
      >
        Work the queue
      </button>
      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
    </form>
  );
}
