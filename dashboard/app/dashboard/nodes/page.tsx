"use client";

import { useEffect, useRef, useState } from "react";
import { fetchNodes, FieldNode } from "../../../lib/api";
import { Card } from "../../../components/ui/Card";
import { SectionHeader } from "../../../components/ui/SectionHeader";
import { StatusBadge } from "../../../components/ui/StatusBadge";
import { useForestWebSocket } from "../../../lib/ws";

function BatteryBar({ level }: { level: number | null }) {
  if (level === null) {
    return <span style={{ fontSize: "0.8rem", color: "#94a3b8" }}>Not reported</span>;
  }
  const color = level > 60 ? "#16a34a" : level > 30 ? "#d97706" : "#dc2626";
  return (
    <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
      <div style={{ width: "80px", height: "10px", background: "#e2e8f0", borderRadius: "5px", overflow: "hidden" }}>
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
    <div className="dashboard-page" style={{ padding: "1.5rem" }}>
      <header className="page-header" style={{ marginBottom: "1.5rem" }}>
        <h1 style={{ fontSize: "1.75rem", fontWeight: 700, color: "var(--color-navy)" }}>Field Node Monitoring</h1>
        <p style={{ color: "#64748b", marginTop: "4px" }}>
          Deployed ESP32-based field nodes — Checkpoint Nodes (patrol verification) and Acoustic Nodes (TinyML threat detection).
        </p>
      </header>

      {/* SUMMARY METRICS */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(200px, 1fr))", gap: "1rem", marginBottom: "1.5rem" }}>
        <Card style={{ padding: "1.25rem", borderLeft: "4px solid var(--color-navy)" }}>
          <p style={{ fontSize: "0.8rem", fontWeight: 700, color: "#64748b" }}>TOTAL NODES</p>
          <p style={{ fontSize: "2rem", fontWeight: 700, color: "var(--color-navy)" }}>{loading ? "..." : nodes.length}</p>
        </Card>
        <Card style={{ padding: "1.25rem", borderLeft: "4px solid #16a34a" }}>
          <p style={{ fontSize: "0.8rem", fontWeight: 700, color: "#64748b" }}>HEALTHY</p>
          <p style={{ fontSize: "2rem", fontWeight: 700, color: "#16a34a" }}>{loading ? "..." : healthyCount}</p>
        </Card>
        <Card style={{ padding: "1.25rem", borderLeft: "4px solid #d97706" }}>
          <p style={{ fontSize: "0.8rem", fontWeight: 700, color: "#64748b" }}>DEGRADED / OFFLINE</p>
          <p style={{ fontSize: "2rem", fontWeight: 700, color: degradedCount > 0 ? "#d97706" : "#16a34a" }}>{loading ? "..." : degradedCount}</p>
        </Card>
      </div>

      {/* NODE CARDS GRID */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(320px, 1fr))", gap: "1rem", marginBottom: "1.5rem" }}>
        {loading ? (
          <p>Loading field nodes...</p>
        ) : (
          nodes.map((n) => (
            <Card
              key={n.id}
              style={{
                padding: "1.25rem",
                borderLeft: `4px solid ${n.health === "HEALTHY" ? "#16a34a" : "#d97706"}`,
                background: n.health === "DEGRADED" ? "#fffbeb" : n.health === "OFFLINE" ? "#fef2f2" : undefined,
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "0.75rem" }}>
                <div>
                  <h3 style={{ fontSize: "1.1rem", fontWeight: 700, color: "var(--color-navy)" }}>{n.nodeId}</h3>
                  <span style={{ fontSize: "0.8rem", fontWeight: 600, color: "#64748b", background: "#f1f5f9", padding: "2px 8px", borderRadius: "12px" }}>
                    {n.nodeType.replace("_", " ")}
                  </span>
                </div>
                <StatusBadge label={n.health ?? "UNKNOWN"} tone={n.health === "HEALTHY" ? "healthy" : "warning"} />
              </div>
              <div style={{ fontSize: "0.85rem", color: "#475569", display: "flex", flexDirection: "column", gap: "5px" }}>
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
                  <span style={{ fontSize: "0.78rem", color: "#94a3b8" }}>FW: {n.firmwareVersion}</span>
                </div>
                <div style={{ marginTop: "4px", fontSize: "0.78rem", color: "#94a3b8" }}>
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
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.88rem" }}>
            <thead>
              <tr style={{ borderBottom: "2px solid #e2e8f0", textAlign: "left", color: "#475569" }}>
                <th style={{ padding: "10px" }}>Node ID</th>
                <th style={{ padding: "10px" }}>Type</th>
                <th style={{ padding: "10px" }}>Checkpoint</th>
                <th style={{ padding: "10px" }}>Zone</th>
                <th style={{ padding: "10px" }}>LoRa</th>
                <th style={{ padding: "10px" }}>RTC</th>
                <th style={{ padding: "10px" }}>Battery</th>
                <th style={{ padding: "10px" }}>Queue</th>
                <th style={{ padding: "10px" }}>Health</th>
                <th style={{ padding: "10px" }}>Firmware</th>
              </tr>
            </thead>
            <tbody>
              {nodes.map((n) => (
                <tr key={n.id} style={{ borderBottom: "1px solid #f1f5f9" }}>
                  <td style={{ padding: "10px", fontWeight: 700, color: "var(--color-navy)" }}>{n.nodeId}</td>
                  <td style={{ padding: "10px", fontSize: "0.8rem" }}>{n.nodeType.replace("_", " ")}</td>
                  <td style={{ padding: "10px" }}>{n.checkpointId}</td>
                  <td style={{ padding: "10px" }}>{n.zone}</td>
                  <td style={{ padding: "10px" }}><StatusBadge label={n.loraActivity ?? "NOT REPORTED"} tone={n.loraActivity === "ACTIVE" ? "healthy" : "warning"} /></td>
                  <td style={{ padding: "10px" }}><StatusBadge label={n.rtcState ?? "NOT REPORTED"} tone={n.rtcState === "SYNCED" ? "healthy" : "warning"} /></td>
                  <td style={{ padding: "10px" }}><BatteryBar level={n.batteryLevel} /></td>
                  <td style={{ padding: "10px" }}>{n.localQueueState ?? "—"}</td>
                  <td style={{ padding: "10px" }}><StatusBadge label={n.health ?? "UNKNOWN"} tone={n.health === "HEALTHY" ? "healthy" : "warning"} /></td>
                  <td style={{ padding: "10px", fontSize: "0.8rem", color: "#64748b" }}>{n.firmwareVersion}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}
