import { useCallback, useEffect, useState } from "react";
import { errorMessage, getJson, postJson } from "./api";
import { StateChip } from "./components/StateChip";
import {
  formatDate,
  formatMoney,
  formatTime,
  humanize,
  roundMoney,
} from "./format";
import { useInterval } from "./hooks";
import type { ClaimEvent, ClaimView, Decision } from "./types";

function DecisionPanel({ decision }: { readonly decision: Decision | null }) {
  if (decision === null) {
    return <p className="muted">No decision yet.</p>;
  }
  return (
    <dl className="facts">
      <dt>Decision</dt>
      <dd>{humanize(decision.decision)}</dd>
      <dt>Payout</dt>
      <dd className="mono">{formatMoney(decision.payout)}</dd>
      <dt>Policy section</dt>
      <dd>{decision.policy_section}</dd>
      <dt>Explanation</dt>
      <dd>{decision.explanation}</dd>
    </dl>
  );
}

function PaymentPanel(props: {
  readonly view: ClaimView;
  readonly onPay: (amount: number) => void;
  readonly onSignOff: () => void;
}) {
  const { view, onPay, onSignOff } = props;
  const decision = view.decision;
  const remaining =
    decision?.decision === "approve"
      ? roundMoney(decision.payout - view.paid_total)
      : 0;
  const waiting = view.state === "waiting for sign-off";

  return (
    <div className="stack">
      <p>
        Paid <span className="mono">{formatMoney(view.paid_total)}</span> so
        far.
      </p>
      {waiting && (
        <p className="notice raspberry">
          This payout is over the approval limit and waits for a handler&apos;s
          sign-off.
        </p>
      )}
      <div className="actions">
        {waiting && (
          <button type="button" onClick={onSignOff}>
            Sign off
          </button>
        )}
        <button
          type="button"
          onClick={() => {
            onPay(remaining);
          }}
          disabled={view.state !== "decided" || remaining <= 0}
        >
          {remaining > 0 ? `Pay ${formatMoney(remaining)}` : "Pay"}
        </button>
      </div>
    </div>
  );
}

function ActivityLog({ events }: { readonly events: ClaimEvent[] }) {
  if (events.length === 0) {
    return <p className="muted">Nothing logged yet.</p>;
  }
  return (
    <ol className="activity">
      {events.map((event, index) => (
        <li key={`${event.created_at}-${String(index)}`}>
          <span className="mono muted">{formatTime(event.created_at)}</span>
          <span className={`kind kind-${event.kind}`}>
            {humanize(event.kind)}
          </span>
          <span>{event.text}</span>
        </li>
      ))}
    </ol>
  );
}

export function ClaimPage({ claimId }: { readonly claimId: string }) {
  const [view, setView] = useState<ClaimView | null>(null);
  const [events, setEvents] = useState<ClaimEvent[]>([]);
  const [error, setError] = useState("");

  const load = useCallback(() => {
    Promise.all([
      getJson<ClaimView>(`/api/claims/${claimId}`),
      getJson<ClaimEvent[]>(`/api/claims/${claimId}/events`),
    ])
      .then(([next, log]) => {
        setView(next);
        setEvents(log);
      })
      .catch((failure: unknown) => {
        setError(errorMessage(failure));
      });
  }, [claimId]);

  useEffect(() => {
    load();
  }, [load]);

  useInterval(load, view?.state === "in progress" ? 2000 : null);

  async function act(path: string, body?: unknown) {
    setError("");
    try {
      await postJson(path, body);
      load();
    } catch (failure) {
      setError(errorMessage(failure));
    }
  }

  if (view === null) {
    return <p className="panel">{error || "Loading the claim..."}</p>;
  }

  const { claim, customer, policy, plan, add_ons: addOns } = view;
  return (
    <div className="claim">
      <section className="panel">
        <div className="panel-head">
          <div>
            <p className="mono muted">{claim.claim_id}</p>
            <h1>{customer.name}</h1>
            <p>
              {humanize(claim.claim_type)}, {claim.incident_location},{" "}
              {formatDate(claim.incident_date)}
            </p>
          </div>
          <div className="stack align-end">
            <StateChip state={view.state} />
            <button
              type="button"
              onClick={() => {
                void act(`/api/claims/${claimId}/run`);
              }}
              disabled={view.state !== "waiting"}
            >
              Run agent
            </button>
          </div>
        </div>
        {error && (
          <p className="alert" role="alert">
            {error}
          </p>
        )}
        <p>{claim.story}</p>
      </section>

      <div className="grid">
        <section className="panel">
          <h2>Items claimed</h2>
          <table>
            <tbody>
              {claim.items.map((item) => (
                <tr key={item.description}>
                  <td>{item.description}</td>
                  <td className="muted">{humanize(item.category)}</td>
                  <td className="num mono">{formatMoney(item.amount)}</td>
                </tr>
              ))}
              <tr>
                <th>Total claimed</th>
                <td />
                <td className="num mono">
                  {formatMoney(claim.amount_claimed)}
                </td>
              </tr>
            </tbody>
          </table>
          <h2>Documents</h2>
          <ul className="documents">
            {claim.documents.map((document) => (
              <li key={document.name}>
                <strong>{document.name}</strong>
                <span className="muted"> {humanize(document.type)}</span>
                <p>{document.content}</p>
              </li>
            ))}
          </ul>
        </section>

        <section className="panel">
          <h2>Policy</h2>
          <dl className="facts">
            <dt>Plan</dt>
            <dd>{plan.name}</dd>
            <dt>Policy</dt>
            <dd className="mono">{policy.policy_id}</dd>
            <dt>Trip</dt>
            <dd>
              {policy.trip.destination}, {formatDate(policy.trip.departs_on)} to{" "}
              {formatDate(policy.trip.returns_on)}
            </dd>
            <dt>Travelers</dt>
            <dd>{policy.travelers.join(", ")}</dd>
            <dt>Add-ons</dt>
            <dd>
              {addOns.length > 0
                ? addOns.map((addOn) => addOn.name).join(", ")
                : "None"}
            </dd>
          </dl>
          <h2>Decision</h2>
          <DecisionPanel decision={view.decision} />
          {view.decision?.decision === "approve" && (
            <>
              <h2>Payment</h2>
              <PaymentPanel
                view={view}
                onPay={(amount) => {
                  void act(`/api/claims/${claimId}/payments`, { amount });
                }}
                onSignOff={() => {
                  void act(`/api/claims/${claimId}/sign-off`);
                }}
              />
            </>
          )}
          <h2>Customer history</h2>
          {customer.previous_claims.length === 0 ? (
            <p className="muted">No earlier claims.</p>
          ) : (
            <ul className="documents">
              {customer.previous_claims.map((previous) => (
                <li key={previous.claim_id}>
                  <strong>{previous.claim_id}</strong>
                  <span className="muted">
                    {" "}
                    {formatDate(previous.filed_on)}
                  </span>
                  <p>
                    {previous.summary}, {humanize(previous.outcome)},{" "}
                    {formatMoney(previous.amount_paid)}
                  </p>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>

      <section className="panel">
        <h2>Activity</h2>
        <ActivityLog events={events} />
      </section>
    </div>
  );
}
