import { useCallback } from "react";
import {
  getClaimHistory,
  getPolicy,
  type Claim,
  type ClaimHistory,
  type Policy,
} from "./api";
import { date, label, money } from "./format";
import { usePolling } from "./hooks";

export function ClaimDetails({ claim }: Readonly<{ claim: Claim }>) {
  return (
    <>
      <section className="card section" aria-label="The claim">
        <h2>The customer&apos;s story</h2>
        <p>{claim.story}</p>
        <table>
          <thead>
            <tr>
              <th scope="col">Item</th>
              <th scope="col">Category</th>
              <th scope="col" className="amount">
                Amount
              </th>
            </tr>
          </thead>
          <tbody>
            {claim.items.map((item) => (
              <tr key={item.description}>
                <td>{item.description}</td>
                <td>{label(item.category)}</td>
                <td className="amount mono">{money(item.amount)}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <h3>Documents</h3>
        <div className="documents">
          {claim.documents.map((document) => (
            <details key={document.name}>
              <summary>
                {document.name}{" "}
                <span className="muted">{label(document.type)}</span>
              </summary>
              <p>{document.content}</p>
            </details>
          ))}
        </div>
      </section>
      <Records policyId={claim.policy_id} customerId={claim.customer_id} />
    </>
  );
}

function Records({
  policyId,
  customerId,
}: Readonly<{ policyId: string; customerId: string }>) {
  const loadPolicy = useCallback(() => getPolicy(policyId), [policyId]);
  const loadHistory = useCallback(
    () => getClaimHistory(customerId),
    [customerId],
  );
  const { data: policy } = usePolling(loadPolicy, null);
  const { data: history } = usePolling(loadHistory, null);
  return (
    <div className="records">
      {policy && <PolicyCard policy={policy} />}
      {history && <HistoryCard history={history} />}
    </div>
  );
}

function PolicyCard({ policy }: Readonly<{ policy: Policy }>) {
  const { trip } = policy;
  return (
    <section className="card section" aria-label="Policy">
      <h2>
        Policy <span className="mono muted">{policy.policy_id}</span>
      </h2>
      <dl className="pairs">
        <dt>Plan</dt>
        <dd>{label(policy.plan)}</dd>
        <dt>Add-ons</dt>
        <dd>{policy.add_ons.map(label).join(", ") || "None"}</dd>
        <dt>Trip</dt>
        <dd>{trip.destination}</dd>
        <dt>Dates</dt>
        <dd>
          {date(trip.departs_on)} to {date(trip.returns_on)}
        </dd>
        <dt>Trip cost</dt>
        <dd className="mono">{money(trip.trip_cost)}</dd>
        <dt>Travelers</dt>
        <dd>{policy.travelers.join(", ")}</dd>
        <dt>Bought</dt>
        <dd>{date(policy.purchased_on)}</dd>
      </dl>
    </section>
  );
}

function HistoryCard({ history }: Readonly<{ history: ClaimHistory }>) {
  return (
    <section className="card section" aria-label="Earlier claims">
      <h2>Earlier claims</h2>
      <p className="muted small">
        Customer since {date(history.customer_since)}
      </p>
      {history.previous_claims.length === 0 && <p>No earlier claims.</p>}
      <ul className="history">
        {history.previous_claims.map((earlier) => (
          <li key={earlier.claim_id}>
            <span className="mono">{earlier.claim_id}</span>{" "}
            <span className="muted">{date(earlier.filed_on)}</span>
            <p>{earlier.summary}</p>
            <p className="muted">
              {label(earlier.outcome)}, paid{" "}
              <span className="mono">{money(earlier.amount_paid)}</span>
            </p>
          </li>
        ))}
      </ul>
    </section>
  );
}
