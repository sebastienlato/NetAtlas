import { useEffect, useRef, useState } from "react";
import { readQuery } from "./api/client";
import type { Snapshot } from "./api/schema";

// Separate document/view: no measurement controls, query values or source identities.
export function OperationsDashboard() {
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null);
  const [message, setMessage] = useState(
    "Refresh to inspect local operations.",
  );
  const [busy, setBusy] = useState(false);
  const active = useRef<AbortController | null>(null);
  const generation = useRef(0);
  useEffect(() => {
    const clear = () => {
      generation.current++;
      active.current?.abort();
      setSnapshot(null);
      setMessage("Snapshot cleared. Refresh for current state.");
    };
    const hide = () => {
      if (document.hidden) clear();
    };
    document.addEventListener("visibilitychange", hide);
    window.addEventListener("pagehide", clear);
    return () => {
      document.removeEventListener("visibilitychange", hide);
      window.removeEventListener("pagehide", clear);
      generation.current++;
      active.current?.abort();
    };
  }, []);
  useEffect(() => {
    if (!snapshot) return;
    const timer = window.setTimeout(() => {
      setSnapshot(null);
      setMessage("Snapshot expired. Refresh for current state.");
    }, 60000);
    return () => window.clearTimeout(timer);
  }, [snapshot]);
  async function refresh() {
    if (active.current) return;
    const controller = new AbortController();
    active.current = controller;
    const current = ++generation.current;
    setSnapshot(null);
    setBusy(true);
    setMessage("Checking dependencies and stored state…");
    try {
      const result = await readQuery(
        "operations",
        { schema_version: 1 },
        { signal: controller.signal },
      );
      if (current !== generation.current || document.hidden) return;
      setSnapshot(result);
      setMessage(
        "Snapshot loaded. Refresh manually; this view expires after 60 seconds.",
      );
    } catch {
      if (current === generation.current)
        setMessage("Operations unavailable or busy. Retry explicitly.");
    } finally {
      active.current = null;
      setBusy(false);
    }
  }
  return (
    <main className="operations" id="main">
      <a href="/">Back to explorer</a>
      <h1>Local operations</h1>
      <p>
        Authored synthetic laboratory only. Counts describe stored work and
        sources, never devices or worldwide coverage.
      </p>
      <button type="button" onClick={() => void refresh()} disabled={busy}>
        Refresh operations
      </button>
      <p role="status">{message}</p>
      {snapshot && (
        <>
          <h2>Dependencies: {snapshot.readiness.status}</h2>
          <p>
            Database {snapshot.readiness.database} · Migration{" "}
            {snapshot.readiness.migration} · Blob access{" "}
            {snapshot.readiness.blobs} · Disk capacity{" "}
            {snapshot.readiness.capacity}
          </p>
          <p>
            Checked at {snapshot.checked_at}. Liveness alone does not establish
            readiness or integrity.
          </p>
          <h2>
            {snapshot.global_stopped
              ? "New work stopped"
              : "New admission allowed"}
          </h2>
          <p>
            Reopening never revives cancelled work. This dashboard has no
            operational controls.
          </p>
          <h2>Stored job states</h2>
          <table>
            <caption>
              States last committed by control operations; this read never
              reconciles leases.
            </caption>
            <thead>
              <tr>
                <th scope="col">State</th>
                <th scope="col">Jobs</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(snapshot.stored_jobs).map(([state, count]) => (
                <tr key={state}>
                  <th scope="row">{state}</th>
                  <td>{count}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <dl>
            <dt>Overdue current leases awaiting reconciliation</dt>
            <dd>{snapshot.overdue_leases}</dd>
            <dt>Central permits issued (including burned grants)</dt>
            <dd>{snapshot.permits_issued}</dd>
            <dt>Committed delivery receipts</dt>
            <dd>{snapshot.delivery_receipts}</dd>
            <dt>Unexpired, unsuppressed retained sources</dt>
            <dd>{snapshot.retained_sources}</dd>
            <dt>Stored sources due for removal</dt>
            <dd>{snapshot.removal_due_sources}</dd>
            <dt>Stored outbox events</dt>
            <dd>{snapshot.outbox_events}</dd>
            <dt>Registered workers / heartbeats within 10 seconds</dt>
            <dd>
              {snapshot.registered_workers} / {snapshot.recent_workers}
            </dd>
            <dt>Free bytes on blob filesystem</dt>
            <dd>{snapshot.blob_free_bytes}</dd>
          </dl>
          <p>
            Receipts and retained sources overlap; they are not additive. Idle
            workers normally exit. Recent heartbeats do not prove measurement
            progress. Outbox events are not external delivery lag; no external
            consumer exists.
          </p>
          <p>
            Readiness checks connectivity, migration and directory access only.
            Use the operator runbook for full source verification, backups,
            opt-outs and recovery. No backup freshness, physical erasure or
            worker-copy deletion is inferred here.
          </p>
        </>
      )}
    </main>
  );
}
