"use client";

import { useEffect, useRef, useState } from "react";
import { fetchSyncHistory, SyncLog } from "../../../lib/api";
import { Card } from "../../../components/ui/Card";
import { SectionHeader } from "../../../components/ui/SectionHeader";
import { StatusBadge } from "../../../components/ui/StatusBadge";
import { useForestWebSocket } from "../../../lib/ws";

export default function SyncHistoryPage() {
  const [logs, setLogs] = useState<SyncLog[]>([]);
  const [loading, setLoading] = useState(true);
  const loadRef = useRef<() => void>(() => {});

  useEffect(() => {
    async function load() {
      const data = await fetchSyncHistory();
      setLogs(data);
      setLoading(false);
    }
    loadRef.current = load;
    load();
  }, []);

  useForestWebSocket(
    ["SYNC_UPDATED"],
    () => loadRef.current(),
    () => loadRef.current()
  );

  const successCount = logs.filter((l) => l.syncResult === "SUCCESS").length;
  const failedCount = logs.filter((l) => l.syncResult === "FAILED").length;

  return (
    <div className="dashboard-page">
      <header className="page-header">
        <h1>Sync history</h1>
        <p>Records forwarded from the gateway to the backend.</p>
      </header>

      <div className="stat-grid">
        <Card className="stat">
          <p className="stat-label">Successful syncs</p>
          <p className="stat-value" style={{ color: "var(--color-healthy)" }}>{loading ? "..." : successCount}</p>
        </Card>
        <Card className="stat">
          <p className="stat-label">Failed</p>
          <p className="stat-value" style={{ color: failedCount > 0 ? "var(--color-danger)" : "var(--color-healthy)" }}>{loading ? "..." : failedCount}</p>
        </Card>
        <Card className="stat">
          <p className="stat-label">Total events</p>
          <p className="stat-value" style={{ color: "var(--color-navy)" }}>{loading ? "..." : logs.length}</p>
        </Card>
      </div>

      <Card>
        <SectionHeader title="Synchronization Event Log" />
        <div style={{ padding: "1rem", overflowX: "auto" }}>
          {loading ? (
            <p>Loading sync history...</p>
          ) : (
            <table>
              <thead>
                <tr>
                  <th>Event ID</th>
                  <th>Node</th>
                  <th>Field Event Created</th>
                  <th>Gateway Received</th>
                  <th>Backend Received</th>
                  <th>Sync Result</th>
                  <th>Retries</th>
                  <th>Duplicate State</th>
                  <th>Verification</th>
                </tr>
              </thead>
              <tbody>
                {logs.map((l) => (
                  <tr key={l.id}>
                    <td>{l.eventId}</td>
                    <td><code>{l.nodeId}</code></td>
                    <td>{l.eventTimestamp}</td>
                    <td>{l.gatewayReceiveTime}</td>
                    <td>{l.backendReceiveTime}</td>
                    <td>
                      <StatusBadge label={l.syncResult} tone={l.syncResult === "SUCCESS" ? "healthy" : "danger"} />
                    </td>
                    <td>{l.retryCount}</td>
                    <td>
                      <StatusBadge label={l.duplicateState} tone={l.duplicateState === "UNIQUE" ? "healthy" : "warning"} />
                    </td>
                    <td>
                      <StatusBadge label={l.verificationResult} tone={l.verificationResult === "PASSED" ? "healthy" : "danger"} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </Card>
    </div>
  );
}
