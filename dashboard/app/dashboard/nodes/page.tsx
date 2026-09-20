"use client";

import { useEffect, useRef, useState } from "react";
import { fetchNodes, FieldNode } from "../../../lib/api";
import { Card } from "../../../components/ui/Card";
import { SectionHeader } from "../../../components/ui/SectionHeader";
import { StatusBadge } from "../../../components/ui/StatusBadge";
import { useForestWebSocket } from "../../../lib/ws";

function BatteryBar({ level }: { level: number | null }) {
  if (level === null) {
    return <span style={{ fontSize: "0.8rem", color: "var(--color-faint)" }}>Not reported</span>;
  }
  const color = level > 60 ? "var(--color-healthy)" : level > 30 ? "var(--color-warning)" : "var(--color-danger)";
  return (
    <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
      <div style={{ width: "80px", height: "10px", background: "var(--color-border)", borderRadius: "5px", overflow: "hidden" }}>
        <div style={{ width: `${level}%`, height: "100%", background: color, borderRadius: "5px", transition: "width 0.3s" }} />
      </div>
      <span style={{ fontSize: "0.8rem", fontWeight: 600, color }}>{level}%</span>
    </div>
  );
}

export default function NodesPage() {
  const [nodes, setNodes] = useState<FieldNode[]>([]);
  const [loading, setLoading] = useState(true);
  const loadRef = useRef<() => void>(() => {});

  useEffect(() => {
    async function load() {
      const data = await fetchNodes();
      setNodes(data);
      setLoading(false);
    }
    loadRef.current = load;
    load();
    const interval = setInterval(load, 15000);
    return () => clearInterval(interval);
  }, []);

  useForestWebSocket(
    ["NODE_STATUS_CHANGED"],
    () => loadRef.current(),
    () => loadRef.current()
  );

  const healthyCount = nodes.filter((n) => n.health === "HEALTHY").length;
  const degradedCount = nodes.filter((n) => n.health === "DEGRADED").length;

  return (
    <div className="dashboard-page">
      <header className="page-header">
        <h1>Field nodes</h1>
        <p>Registered nodes, the checkpoint each one is attached to, and when it was last heard.</p>
      </header>

      {/* SUMMARY METRICS */}
      <div className="stat-grid">
        <Card className="stat">
          <p className="stat-label">Total nodes</p>
          <p className="stat-value" style={{ color: "var(--color-navy)" }}>{loading ? "..." : nodes.length}</p>
        </Card>
        <Card className="stat">
          <p className="stat-label">Healthy</p>
          <p className="stat-value" style={{ color: "var(--color-healthy)" }}>{loading ? "..." : healthyCount}</p>
        </Card>
        <Card className="stat">
          <p className="stat-label">DEGRADED / OFFLINE</p>
          <p className="stat-value" style={{ color: degradedCount > 0 ? "var(--color-warning)" : "var(--color-healthy)" }}>{loading ? "..." : degradedCount}</p>
        </Card>
      </div>

      {/* NODE CARDS GRID */}
      <div className="stat-grid">
        {loading ? (
          <p>Loading field nodes...</p>
        ) : (
          nodes.map((n) => (
            <Card
              key={n.id}
              style={{
                padding: "1.25rem",
                background: n.health === "DEGRADED" ? "var(--color-warning-bg)" : n.health === "OFFLINE" ? "var(--color-danger-bg)" : undefined,
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "0.75rem" }}>
                <div>
                  <h3 style={{ fontSize: "1.1rem", fontWeight: 700, color: "var(--color-navy)" }}>{n.nodeId}</h3>
                  <span style={{ fontSize: "0.8rem", fontWeight: 600, color: "var(--color-muted)", background: "var(--color-surface-alt)", padding: "2px 8px", borderRadius: "12px" }}>
                    {n.nodeType.replace("_", " ")}
                  </span>
                </div>
                <StatusBadge label={n.health ?? "UNKNOWN"} tone={n.health === "HEALTHY" ? "healthy" : "warning"} />
              </div>
              <div style={{ fontSize: "0.85rem", color: "var(--color-text-soft)", display: "flex", flexDirection: "column", gap: "5px" }}>
                <div style={{ display: "flex", justifyContent: "space-between" }}>
                  <span><strong>Checkpoint:</strong> {n.checkpointId}</span>
                  <span><strong>Zone:</strong> {n.zone}</span>
                </div>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <span><strong>LoRa Activity:</strong></span>
                  <StatusBadge label={n.loraActivity ?? "NOT REPORTED"} tone={n.loraActivity === "ACTIVE" ? "healthy" : "warning"} />
                </div>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <span><strong>RTC State:</strong></span>
                  <StatusBadge label={n.rtcState ?? "NOT REPORTED"} tone={n.rtcState === "SYNCED" ? "healthy" : "warning"} />
                </div>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <span><strong>Battery:</strong></span>
                  <BatteryBar level={n.batteryLevel} />
                </div>
                <div style={{ display: "flex", justifyContent: "space-between" }}>
                  <span style={{ fontSize: "0.8rem" }}><strong>Local Queue:</strong> {n.localQueueState ?? "—"} records</span>
                  <span style={{ fontSize: "0.78rem", color: "var(--color-faint)" }}>FW: {n.firmwareVersion}</span>
                </div>
                <div style={{ marginTop: "4px", fontSize: "0.78rem", color: "var(--color-faint)" }}>
                  Last Event: {n.lastEventTime ?? "—"} | Last Sync: {n.lastSyncTime ?? "—"}
                </div>
              </div>
            </Card>
          ))
        )}
      </div>

      {/* TABLE VIEW */}
      <Card>
        <SectionHeader title="Field Node Status Table" />
        <div style={{ padding: "1rem", overflowX: "auto" }}>
          <table>
            <thead>
              <tr>
                <th>Node ID</th>
                <th>Type</th>
                <th>Checkpoint</th>
                <th>Zone</th>
                <th>LoRa</th>
                <th>RTC</th>
                <th>Battery</th>
                <th>Queue</th>
                <th>Health</th>
                <th>Firmware</th>
              </tr>
            </thead>
            <tbody>
              {nodes.map((n) => (
                <tr key={n.id}>
                  <td>{n.nodeId}</td>
                  <td>{n.nodeType.replace("_", " ")}</td>
                  <td>{n.checkpointId}</td>
                  <td>{n.zone}</td>
                  <td><StatusBadge label={n.loraActivity ?? "NOT REPORTED"} tone={n.loraActivity === "ACTIVE" ? "healthy" : "warning"} /></td>
                  <td><StatusBadge label={n.rtcState ?? "NOT REPORTED"} tone={n.rtcState === "SYNCED" ? "healthy" : "warning"} /></td>
                  <td><BatteryBar level={n.batteryLevel} /></td>
                  <td>{n.localQueueState ?? "—"}</td>
                  <td><StatusBadge label={n.health ?? "UNKNOWN"} tone={n.health === "HEALTHY" ? "healthy" : "warning"} /></td>
                  <td>{n.firmwareVersion}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}
