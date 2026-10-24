import { listClaims, type ClaimSummary, type Status } from "./api";
import { OUTCOME_LABELS, STATUS_LABELS, date, label, money } from "./format";
import { usePolling } from "./hooks";
import { StatusPill } from "./StatusPill";

const FLOW: Status[] = [
  "waiting",
  "in_progress",
  "waiting_for_sign_off",
  "decided",
];

export function Queue() {
  const { data: claims, failed } = usePolling(listClaims, 2000);
  return (
    <>
      <div className="queue-head">
        <h1>Claims queue</h1>
        {claims && <p className="muted">{claims.length} claims</p>}
      </div>
      {failed && (
        <p className="notice" role="alert">
          The backend is not responding. Start it with npm run dev.
        </p>
      )}
      {claims && (
        <>
          <Flow claims={claims} />
          <ClaimsTable claims={claims} />
        </>
      )}
    </>
  );
}

function Flow({ claims }: Readonly<{ claims: ClaimSummary[] }>) {
  const counts = FLOW.map((status) => ({
    status,
    count: claims.filter((c) => c.status === status).length,
  }));
  return (
    <section>
      <div className="flow" aria-hidden="true">
        {counts
          .filter(({ count }) => count > 0)
          .map(({ status, count }) => (
            <span
              key={status}
              className={`status-${status}`}
              style={{ flexGrow: count }}
            />
          ))}
      </div>
      <ul className="legend" aria-label="Where the claims stand">
        {counts.map(({ status, count }) => (
          <li key={status}>
            <span className={`dot status-${status}`} aria-hidden="true" />
            <span className="count">{count}</span> {STATUS_LABELS[status]}
          </li>
        ))}
      </ul>
    </section>
  );
}

function ClaimsTable({ claims }: Readonly<{ claims: ClaimSummary[] }>) {
  return (
    <div className="card table-card">
      <table>
        <thead>
          <tr>
            <th scope="col">Claim</th>
            <th scope="col">Customer</th>
            <th scope="col">Type</th>
            <th scope="col">Submitted</th>
            <th scope="col" className="amount">
              Claimed
            </th>
            <th scope="col">Status</th>
            <th scope="col">Decision</th>
          </tr>
        </thead>
        <tbody>
          {claims.map((claim) => (
            <tr key={claim.claim_id}>
              <td>
                <a className="mono" href={`#/claims/${claim.claim_id}`}>
                  {claim.claim_id}
                </a>
              </td>
              <td>{claim.customer_name}</td>
              <td>{label(claim.claim_type)}</td>
              <td>{date(claim.submitted_on)}</td>
              <td className="amount mono">{money(claim.amount_claimed)}</td>
              <td>
                <StatusPill status={claim.status} />
              </td>
              <td>
                <DecisionCell claim={claim} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function DecisionCell({ claim }: Readonly<{ claim: ClaimSummary }>) {
  if (claim.outcome === null) return null;
  if (claim.outcome !== "approve") return <>{OUTCOME_LABELS[claim.outcome]}</>;
  return (
    <>
      Approved <span className="mono">{money(claim.payout ?? 0)}</span>
    </>
  );
}
