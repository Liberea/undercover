import { getInstructions } from "./api";
import { usePolling } from "./hooks";

export function Instructions() {
  const { data } = usePolling(getInstructions, null);
  return (
    <>
      <div className="page-head">
        <h1>The agent&apos;s instructions</h1>
        <p className="muted">
          What the UnderCover Agent is told when it works the queue, and when it
          works each claim. Read only.
        </p>
      </div>
      {data && (
        <div className="stack">
          <section className="stack-tight" aria-label="Working the queue">
            <h2>Working the queue</h2>
            <pre className="card instructions">{data.queue}</pre>
          </section>
          <section className="stack-tight" aria-label="Working a claim">
            <h2>Working a claim</h2>
            <pre className="card instructions">{data.claim}</pre>
          </section>
        </div>
      )}
    </>
  );
}
