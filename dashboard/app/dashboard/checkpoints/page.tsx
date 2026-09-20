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
    <div className="dashboard-page">
      <header className="page-header">
        <h1>Checkpoints</h1>
        <p>Patrol checkpoints and the node assigned to each.</p>
      </header>

      {/* CARDS GRID SUMMARY */}
      <div className="stat-grid">
        {loading ? (
          <p>Loading checkpoints...</p>
        ) : (
          checkpoints.map((cp) => (
            <Card key={cp.id} style={{ padding: "1.25rem" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.5rem" }}>
                <h3 style={{ fontSize: "1.2rem", fontWeight: 700, color: "var(--color-navy)" }}>{cp.checkpointId}</h3>
                <StatusBadge label={cp.state} tone={cp.state === "ONLINE" ? "healthy" : "warning"} />
              </div>
              <div style={{ fontSize: "0.85rem", color: "var(--color-text-soft)", display: "flex", flexDirection: "column", gap: "4px" }}>
                <div><strong>Node:</strong> {cp.nodeId}</div>
                <div><strong>Zone:</strong> {cp.zone}</div>
                <div><strong>Location:</strong> {cp.location}</div>
                <div><strong>Last Patrol:</strong> {cp.lastPatrolTime}</div>
                <div><strong>Last Sync Event:</strong> {cp.lastSyncEvent}</div>
                <div><strong>Pending Queue:</strong> {cp.pendingRecords} records</div>
                <div style={{ marginTop: "6px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <span style={{ fontSize: "0.75rem", color: "var(--color-muted)" }}>Verification State:</span>
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
          <table>
            <thead>
              <tr>
                <th>Checkpoint ID</th>
                <th>Zone</th>
                <th>Node ID</th>
                <th>Location</th>
                <th>State</th>
                <th>Last Patrol</th>
                <th>Pending Records</th>
                <th>Verification</th>
              </tr>
            </thead>
            <tbody>
              {checkpoints.map((cp) => (
                <tr key={cp.id}>
                  <td>{cp.checkpointId}</td>
                  <td>{cp.zone}</td>
                  <td><code>{cp.nodeId}</code></td>
                  <td>{cp.location}</td>
                  <td>
                    <StatusBadge label={cp.state} tone={cp.state === "ONLINE" ? "healthy" : "warning"} />
                  </td>
                  <td>{cp.lastPatrolTime}</td>
                  <td>{cp.pendingRecords}</td>
                  <td>
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
