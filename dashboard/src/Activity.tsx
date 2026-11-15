import { useCallback } from "react";
import { listSteps, type Step, type StepKind } from "./api";
import { usePolling } from "./hooks";

const KIND_LABELS: Record<StepKind, string> = {
  tool_call: "Tool call",
  tool_result: "Result",
  read: "Read",
  reply: "Reply",
  error: "Stopped",
};

/** A read step's first line names the section; the section's text follows. */
function heading(step: Step): string {
  return step.text.split("\n")[0];
}

export function Activity({
  claimId,
  working,
}: Readonly<{ claimId: string; working: boolean }>) {
  const load = useCallback(() => listSteps(claimId), [claimId]);
  const { data: steps } = usePolling(load, 1000);
  return (
    <section className="card section activity" aria-label="Agent's activity">
      <h2>Agent&apos;s activity</h2>
      {steps?.length === 0 && !working && (
        <p className="muted">The agent has not worked on this claim yet.</p>
      )}
      {steps && <SectionsRead steps={steps} />}
      {steps && steps.length > 0 && (
        <ol className="steps">
          {steps.map((step) => (
            <li key={step.step_id} className={`step step-${step.kind}`}>
              <span className="step-kind">{KIND_LABELS[step.kind]}</span>
              <StepBody step={step} />
            </li>
          ))}
        </ol>
      )}
      {working && (
        <p className="working">
          <span className="dot" aria-hidden="true" />
          The agent is working on this claim.
        </p>
      )}
    </section>
  );
}

function SectionsRead({ steps }: Readonly<{ steps: Step[] }>) {
  const read = [
    ...new Set(steps.filter((s) => s.kind === "read").map(heading)),
  ];
  if (read.length === 0) return null;
  return (
    <div className="sections-read">
      <h3>Sections read</h3>
      <ul aria-label="Sections the agent read">
        {read.map((section) => (
          <li key={section}>{section}</li>
        ))}
      </ul>
    </div>
  );
}

function StepBody({ step }: Readonly<{ step: Step }>) {
  if (step.kind === "tool_call") return <p className="mono">{step.text}</p>;
  if (step.kind === "read") {
    return (
      <details>
        <summary>{heading(step)}</summary>
        <pre>{step.text.slice(heading(step).length).trim()}</pre>
      </details>
    );
  }
  if (step.kind !== "tool_result") return <p>{step.text}</p>;
  const [tool, ...rest] = step.text.split(": ");
  return (
    <details>
      <summary className="mono">{tool}</summary>
      <pre>{rest.join(": ")}</pre>
    </details>
  );
}
