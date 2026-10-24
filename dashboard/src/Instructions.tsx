import { getInstructions } from "./api";
import { usePolling } from "./hooks";

export function Instructions() {
  const { data } = usePolling(getInstructions, null);
  return (
    <>
      <div className="page-head">
        <h1>The agent&apos;s instructions</h1>
        <p className="muted">
          What the UnderCover Agent is told to do on every claim. Read only.
        </p>
      </div>
      {data && <pre className="card instructions">{data.text}</pre>}
    </>
  );
}
