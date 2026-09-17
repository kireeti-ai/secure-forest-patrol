"use client";

import { useEffect, useState } from "react";
import { fetchCheckpoints, Checkpoint } from "../../../lib/api";
import { Card } from "../../../components/ui/Card";
import { SectionHeader } from "../../../components/ui/SectionHeader";
import { StatusBadge } from "../../../components/ui/StatusBadge";

export default function CheckpointsPage() {
  const [checkpoints, setCheckpoints] = useState<Checkpoint[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      const data = await fetchCheckpoints();
      setCheckpoints(data);
      setLoading(false);
    }
    load();
  }, []);

  return (
    <div className="dashboard-page" style={{ padding: "1.5rem" }}>
      <header className="page-header" style={{ marginBottom: "1.5rem" }}>
        <h1 style={{ fontSize: "1.75rem", fontWeight: 700, color: "var(--color-navy)" }}>Checkpoint Management & Monitoring</h1>
        <p style={{ color: "#64748b", marginTop: "4px" }}>
          Configured forest patrol checkpoints and assigned field nodes.
        </p>
      </header>

      {/* CARDS GRID SUMMARY */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))", gap: "1rem", marginBottom: "1.5rem" }}>
        {loading ? (
          <p>Loading checkpoints...</p>
        ) : (
          checkpoints.map((cp) => (
            <Card key={cp.id} style={{ padding: "1.25rem", borderLeft: "4px solid var(--color-navy)" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.5rem" }}>
                <h3 style={{ fontSize: "1.2rem", fontWeight: 700, color: "var(--color-navy)" }}>{cp.checkpointId}</h3>
                <StatusBadge label={cp.state} tone={cp.state === "ONLINE" ? "healthy" : "warning"} />
              </div>
              <div style={{ fontSize: "0.85rem", color: "#475569", display: "flex", flexDirection: "column", gap: "4px" }}>
                <div><strong>Node:</strong> {cp.nodeId}</div>
                <div><strong>Zone:</strong> {cp.zone}</div>
                <div><strong>Location:</strong> {cp.location}</div>
                <div><strong>Last Patrol:</strong> {cp.lastPatrolTime}</div>
                <div><strong>Last Sync Event:</strong> {cp.lastSyncEvent}</div>
                <div><strong>Pending Queue:</strong> {cp.pendingRecords} records</div>
                <div style={{ marginTop: "6px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <span style={{ fontSize: "0.75rem", color: "#64748b" }}>Verification State:</span>
                  <StatusBadge label={cp.verificationState} tone={cp.verificationState === "VERIFIED" ? "healthy" : "danger"} />
                </div>
              </div>
            </Card>
          ))
        )}
      </div>

      {/* TABLE VIEW */}
      <Card>
        <SectionHeader title="All Registered Checkpoints" />
        <div style={{ padding: "1rem", overflowX: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.9rem" }}>
            <thead>
              <tr style={{ borderBottom: "2px solid #e2e8f0", textAlign: "left", color: "#475569" }}>
                <th style={{ padding: "10px" }}>Checkpoint ID</th>
                <th style={{ padding: "10px" }}>Zone</th>
                <th style={{ padding: "10px" }}>Node ID</th>
                <th style={{ padding: "10px" }}>Location</th>
                <th style={{ padding: "10px" }}>State</th>
                <th style={{ padding: "10px" }}>Last Patrol</th>
                <th style={{ padding: "10px" }}>Pending Records</th>
                <th style={{ padding: "10px" }}>Verification</th>
              </tr>
            </thead>
            <tbody>
              {checkpoints.map((cp) => (
                <tr key={cp.id} style={{ borderBottom: "1px solid #f1f5f9" }}>
                  <td style={{ padding: "10px", fontWeight: 700, color: "var(--color-navy)" }}>{cp.checkpointId}</td>
                  <td style={{ padding: "10px" }}>{cp.zone}</td>
                  <td style={{ padding: "10px" }}><code>{cp.nodeId}</code></td>
                  <td style={{ padding: "10px" }}>{cp.location}</td>
                  <td style={{ padding: "10px" }}>
                    <StatusBadge label={cp.state} tone={cp.state === "ONLINE" ? "healthy" : "warning"} />
                  </td>
                  <td style={{ padding: "10px" }}>{cp.lastPatrolTime}</td>
                  <td style={{ padding: "10px" }}>{cp.pendingRecords}</td>
                  <td style={{ padding: "10px" }}>
                    <StatusBadge label={cp.verificationState} tone={cp.verificationState === "VERIFIED" ? "healthy" : "danger"} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}
