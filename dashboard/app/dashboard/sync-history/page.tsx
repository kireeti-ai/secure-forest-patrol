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
    <div className="dashboard-page" style={{ padding: "1.5rem" }}>
      <header className="page-header" style={{ marginBottom: "1.5rem" }}>
        <h1 style={{ fontSize: "1.75rem", fontWeight: 700, color: "var(--color-navy)" }}>Offline DTN Synchronization History</h1>
        <p style={{ color: "#64748b", marginTop: "4px" }}>
          End-to-end event delivery log — from field event creation, to gateway receipt (LoRa), to backend delivery (Wi-Fi backhaul).
        </p>
      </header>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(200px, 1fr))", gap: "1rem", marginBottom: "1.5rem" }}>
        <Card style={{ padding: "1.25rem", borderLeft: "4px solid #16a34a" }}>
          <p style={{ fontSize: "0.8rem", fontWeight: 700, color: "#64748b" }}>SUCCESSFUL SYNCS</p>
          <p style={{ fontSize: "2rem", fontWeight: 700, color: "#16a34a" }}>{loading ? "..." : successCount}</p>
        </Card>
        <Card style={{ padding: "1.25rem", borderLeft: "4px solid #dc2626" }}>
          <p style={{ fontSize: "0.8rem", fontWeight: 700, color: "#64748b" }}>FAILED</p>
          <p style={{ fontSize: "2rem", fontWeight: 700, color: failedCount > 0 ? "#dc2626" : "#16a34a" }}>{loading ? "..." : failedCount}</p>
        </Card>
        <Card style={{ padding: "1.25rem", borderLeft: "4px solid var(--color-navy)" }}>
          <p style={{ fontSize: "0.8rem", fontWeight: 700, color: "#64748b" }}>TOTAL EVENTS</p>
          <p style={{ fontSize: "2rem", fontWeight: 700, color: "var(--color-navy)" }}>{loading ? "..." : logs.length}</p>
        </Card>
      </div>

      <Card>
        <SectionHeader title="Synchronization Event Log" />
        <div style={{ padding: "1rem", overflowX: "auto" }}>
          {loading ? (
            <p>Loading sync history...</p>
          ) : (
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.88rem" }}>
              <thead>
                <tr style={{ borderBottom: "2px solid #e2e8f0", textAlign: "left", color: "#475569" }}>
                  <th style={{ padding: "10px" }}>Event ID</th>
                  <th style={{ padding: "10px" }}>Node</th>
                  <th style={{ padding: "10px" }}>Field Event Created</th>
                  <th style={{ padding: "10px" }}>Gateway Received</th>
                  <th style={{ padding: "10px" }}>Backend Received</th>
                  <th style={{ padding: "10px" }}>Sync Result</th>
                  <th style={{ padding: "10px" }}>Retries</th>
                  <th style={{ padding: "10px" }}>Duplicate State</th>
                  <th style={{ padding: "10px" }}>Verification</th>
                </tr>
              </thead>
              <tbody>
                {logs.map((l) => (
                  <tr key={l.id} style={{ borderBottom: "1px solid #f1f5f9" }}>
                    <td style={{ padding: "10px", fontWeight: 700, color: "var(--color-navy)" }}>{l.eventId}</td>
                    <td style={{ padding: "10px" }}><code>{l.nodeId}</code></td>
                    <td style={{ padding: "10px" }}>{l.eventTimestamp}</td>
                    <td style={{ padding: "10px" }}>{l.gatewayReceiveTime}</td>
                    <td style={{ padding: "10px" }}>{l.backendReceiveTime}</td>
                    <td style={{ padding: "10px" }}>
                      <StatusBadge label={l.syncResult} tone={l.syncResult === "SUCCESS" ? "healthy" : "danger"} />
                    </td>
                    <td style={{ padding: "10px" }}>{l.retryCount}</td>
                    <td style={{ padding: "10px" }}>
                      <StatusBadge label={l.duplicateState} tone={l.duplicateState === "UNIQUE" ? "healthy" : "warning"} />
                    </td>
                    <td style={{ padding: "10px" }}>
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
