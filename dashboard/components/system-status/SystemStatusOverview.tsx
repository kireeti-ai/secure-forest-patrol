"use client";

import { useEffect, useState } from "react";
import { fetchForestSystemStatus, ForestSystemStatus } from "../../lib/api";
import { Card } from "../ui/Card";
import { StatusBadge } from "../ui/StatusBadge";

export function SystemStatusOverview() {
  const [status, setStatus] = useState<ForestSystemStatus | null>(null);

  useEffect(() => {
    let mounted = true;
    async function load() {
      const data = await fetchForestSystemStatus();
      if (!mounted) return;
      setStatus(data);
    }
    load();
    const interval = setInterval(load, 10000);
    return () => { mounted = false; clearInterval(interval); };
  }, []);

  const components = status ? [
    status.fieldLayer,
    status.gateway,
    status.wifiBackhaul,
    status.backend,
    status.database,
    status.ledgerVerification,
  ] : [];
  const loraConnected = status && status.gateway.status === "CONNECTED" && status.fieldLayer.status === "OPERATIONAL";

  return (
    <div className="system-status-page">
      <header className="system-status-header">
        <h1>System status</h1>
        <p>Health of each part of the pipeline.</p>
      </header>
      {loraConnected && (
        <Card style={{ marginBottom: "1rem", background: "var(--color-healthy-bg)", border: "1px solid var(--color-border)" }}>
          <div style={{ padding: "1rem 1.25rem" }}>
            <strong style={{ color: "var(--color-healthy)" }}>Both the LoRa sensor and the LoRa gateway are connected and running.</strong>
            <p style={{ color: "var(--color-healthy)", margin: "6px 0 0" }}>
              If you want any additional details, tell me which telemetry or node status you would like to inspect.
            </p>
          </div>
        </Card>
      )}
      <Card>
        <div style={{ padding: "1rem", display: "flex", flexDirection: "column", gap: "0.75rem" }}>
          {!status ? (
            <p>Loading system status...</p>
          ) : (
            components.map((c) => (
              <div
                key={c.component}
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  padding: "0.75rem 1rem",
                  background: "var(--color-surface-alt)",
                  border: "1px solid var(--color-border)",
                  borderRadius: "8px",
                }}
              >
                <div>
                  <strong>{c.component}</strong>
                  <p style={{ fontSize: "0.82rem", color: "var(--color-muted)", marginTop: "2px" }}>{c.details}</p>
                </div>
                <StatusBadge
                  label={c.status}
                  tone={["OPERATIONAL","CONNECTED","REACHABLE","HEALTHY"].includes(c.status) ? "healthy" : "warning"}
                />
              </div>
            ))
          )}
        </div>
      </Card>
    </div>
  );
}
