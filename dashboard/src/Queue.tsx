import { useCallback, useEffect, useState } from "react";
import { errorMessage, getJson, postJson } from "./api";
import { StateChip } from "./components/StateChip";
import { formatMoney, humanize } from "./format";
import { useInterval } from "./hooks";
import type { QueueRow } from "./types";

function decisionText(row: QueueRow): string {
  if (row.decision === null) {
    return "None yet";
  }
  if (row.decision === "approve") {
    return `Approve, ${formatMoney(row.payout ?? 0)}`;
  }
  return humanize(row.decision);
}

export function Queue() {
  const [rows, setRows] = useState<QueueRow[]>([]);
  const [loaded, setLoaded] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const load = useCallback(() => {
    getJson<QueueRow[]>("/api/claims")
      .then((data) => {
        setRows(data);
        setLoaded(true);
      })
      .catch((failure: unknown) => {
        setError(errorMessage(failure));
      });
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const running = rows.some((row) => row.state === "in progress");
  useInterval(load, running ? 2000 : null);

  const waiting = rows.filter((row) => row.state === "waiting").length;

  async function workQueue() {
    setError("");
    try {
      const result = await postJson<{ waiting: number }>("/api/runs");
      setMessage(`Working through ${String(result.waiting)} waiting claims.`);
      load();
    } catch (failure) {
      setError(errorMessage(failure));
    }
  }

  return (
    <section className="panel">
      <div className="panel-head">
        <div>
          <h1>Claims queue</h1>
          <p className="muted">{waiting} waiting for the agent</p>
        </div>
        <button
          type="button"
          onClick={() => void workQueue()}
          disabled={waiting === 0}
        >
          Work the queue
        </button>
      </div>
      {message && <p className="notice">{message}</p>}
      {error && (
        <p className="alert" role="alert">
          {error}
        </p>
      )}
      {!loaded && !error && <p className="muted">Loading the queue...</p>}
      {loaded && (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Claim</th>
                <th>Customer</th>
                <th>Type</th>
                <th className="num">Claimed</th>
                <th>State</th>
                <th>Decision</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.claim_id}>
                  <td>
                    <a className="mono" href={`#/claims/${row.claim_id}`}>
                      {row.claim_id}
                    </a>
                  </td>
                  <td>{row.customer_name}</td>
                  <td>{humanize(row.claim_type)}</td>
                  <td className="num mono">
                    {formatMoney(row.amount_claimed)}
                  </td>
                  <td>
                    <StateChip state={row.state} />
                  </td>
                  <td>{decisionText(row)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
