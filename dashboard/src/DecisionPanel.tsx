import { useState } from "react";
import {
  listHandlers,
  message,
  signOff,
  type Claim,
  type Decision,
} from "./api";
import { OUTCOME_LABELS, money } from "./format";
import { usePolling } from "./hooks";

export function DecisionPanel({ claim }: Readonly<{ claim: Claim }>) {
  const { decision } = claim;
  if (!decision) {
    return (
      <section className="card section" aria-label="Decision">
        <h2>Decision</h2>
        <p className="muted">
          {claim.status === "in_progress"
            ? "The agent is working on this claim."
            : "No decision yet. Run the agent to decide this claim."}
        </p>
      </section>
    );
  }
  const waiting = claim.status === "waiting_for_sign_off";
  return (
    <section className="card section" aria-label="Decision">
      <div className="decision-head">
        <h2>{OUTCOME_LABELS[decision.outcome]}</h2>
        {decision.outcome === "approve" && (
          <p className="key-figure mono">{money(decision.payout)}</p>
        )}
      </div>
      <p>{decision.reasons}</p>
      <p className="muted">Policy wording: {decision.policy_section}</p>
      <PaymentLine decision={decision} waiting={waiting} />
      {waiting && <SignOff claimId={claim.claim_id} />}
    </section>
  );
}

function PaymentLine({
  decision,
  waiting,
}: Readonly<{ decision: Decision; waiting: boolean }>) {
  const { payment } = decision;
  if (decision.outcome !== "approve") return null;
  if (payment) {
    const by = payment.signed_off_by;
    return (
      <p className="payment">
        Paid <span className="mono">{money(payment.amount)}</span>
        {by && `, signed off by ${by}`}
      </p>
    );
  }
  if (waiting) {
    return (
      <p className="payment payment-held">
        The payment waits for a handler&apos;s sign-off.
      </p>
    );
  }
  return <p className="payment muted">Not paid yet.</p>;
}

function SignOff({ claimId }: Readonly<{ claimId: string }>) {
  const { data: handlers } = usePolling(listHandlers, null);
  const [handlerId, setHandlerId] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string>();
  return (
    <form
      className="sign-off"
      onSubmit={(event) => {
        event.preventDefault();
        setSending(true);
        signOff(claimId, handlerId).catch((failure: unknown) => {
          setError(message(failure));
          setSending(false);
        });
      }}
    >
      <label>
        Handler
        <select
          value={handlerId}
          onChange={(event) => {
            setHandlerId(event.target.value);
          }}
        >
          <option value="">Choose a handler</option>
          {handlers?.map((handler) => (
            <option key={handler.handler_id} value={handler.handler_id}>
              {handler.name}
            </option>
          ))}
        </select>
      </label>
      <button
        type="submit"
        className="button button-primary"
        disabled={!handlerId || sending}
      >
        Sign off and pay
      </button>
      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
    </form>
  );
}
