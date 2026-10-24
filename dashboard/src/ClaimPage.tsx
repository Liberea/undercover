import { useCallback, useState } from "react";
import { getClaim, message, runAgent, type Claim } from "./api";
import { Activity } from "./Activity";
import { ClaimDetails } from "./ClaimDetails";
import { DecisionPanel } from "./DecisionPanel";
import { date, label, money } from "./format";
import { usePolling } from "./hooks";
import { StatusPill } from "./StatusPill";

export function ClaimPage({ claimId }: Readonly<{ claimId: string }>) {
  const load = useCallback(() => getClaim(claimId), [claimId]);
  const { data: claim, failed } = usePolling(load, 1000);
  return (
    <>
      <p className="back">
        <a href="#/">Claims queue</a>
      </p>
      {failed && !claim && (
        <p className="notice" role="alert">
          Claim {claimId} could not be loaded. Check the claim id and that the
          backend is running.
        </p>
      )}
      {claim && <ClaimView claim={claim} />}
    </>
  );
}

function ClaimView({ claim }: Readonly<{ claim: Claim }>) {
  return (
    <>
      <header className="claim-head">
        <div className="claim-title">
          <h1 className="mono">{claim.claim_id}</h1>
          <StatusPill status={claim.status} />
        </div>
        {claim.status === "waiting" && <RunAgent claimId={claim.claim_id} />}
      </header>
      <p className="lede">{claim.summary}</p>
      <dl className="facts">
        <div>
          <dt>Customer</dt>
          <dd>{claim.customer_name}</dd>
        </div>
        <div>
          <dt>Type</dt>
          <dd>{label(claim.claim_type)}</dd>
        </div>
        <div>
          <dt>Claimed</dt>
          <dd className="mono">{money(claim.amount_claimed)}</dd>
        </div>
        <div>
          <dt>Incident</dt>
          <dd>
            {date(claim.incident_date)}, {claim.incident_location}
          </dd>
        </div>
        <div>
          <dt>Submitted</dt>
          <dd>{date(claim.submitted_on)}</dd>
        </div>
      </dl>
      <div className="claim-grid">
        <div className="stack">
          <DecisionPanel claim={claim} />
          <ClaimDetails claim={claim} />
        </div>
        <Activity
          claimId={claim.claim_id}
          working={claim.status === "in_progress"}
        />
      </div>
    </>
  );
}

function RunAgent({ claimId }: Readonly<{ claimId: string }>) {
  const [starting, setStarting] = useState(false);
  const [error, setError] = useState<string>();
  const start = () => {
    setStarting(true);
    runAgent(claimId).catch((failure: unknown) => {
      setError(message(failure));
      setStarting(false);
    });
  };
  return (
    <div className="run-agent">
      <button
        type="button"
        className="button button-primary"
        disabled={starting}
        onClick={start}
      >
        Run the agent
      </button>
      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
    </div>
  );
}
