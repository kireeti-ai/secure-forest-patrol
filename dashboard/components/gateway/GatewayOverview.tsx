"use client";

import { useEffect, useState } from "react";
import { fetchGateways, fetchSyncHistory, GatewayStatus, SyncLog } from "../../lib/api";
import { Card } from "../ui/Card";
import { SectionHeader } from "../ui/SectionHeader";
import { StatusBadge } from "../ui/StatusBadge";

export function GatewayOverview() {
  const [history, setHistory] = useState<SyncLog[]>([]);
  const [gateway, setGateway] = useState<GatewayStatus | null>(null);

  useEffect(() => {
    let mounted = true;
    async function load() {
      const [syncData, gateways] = await Promise.all([fetchSyncHistory(), fetchGateways()]);
      if (!mounted) return;
      setHistory(syncData);
      setGateway(gateways[0] ?? null);
    }
    load();
    const interval = setInterval(load, 5000);
    return () => { mounted = false; clearInterval(interval); };
  }, []);

  return (
    <div className="gateway-page">
      <header className="gateway-header">
        <h1>Gateway Status</h1>
        <p>Dual-link gateway — LoRa field link (433 MHz) and Wi-Fi backhaul (IP).</p>
      </header>

      <section className="gateway-status-section" aria-label="Gateway status">
        <SectionHeader title="Gateway Connection" />
        <Card className="gateway-status-panel">
          <div className="gateway-status-content" style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <div>
              <p className="gateway-status-title" style={{ fontSize: "1.1rem", fontWeight: 600 }}>
                {gateway ? `Forest Gateway (${gateway.gatewayId})` : "Gateway unavailable"}
              </p>
              <p className="gateway-status-message" style={{ color: "#94a3b8", fontSize: "0.9rem" }}>
                {gateway
                  ? `LoRa: ${gateway.loraStatus} | Wi-Fi: ${gateway.wifiStatus} | Backend: ${gateway.backendStatus}`
                  : "No gateway record currently available from the backend."}
              </p>
            </div>
            <StatusBadge
              label={gateway?.status ?? "UNAVAILABLE"}
              tone={gateway?.status === "ONLINE" ? "healthy" : "neutral"}
            />
          </div>
        </Card>
      </section>

      <section className="gateway-activity-section" style={{ marginTop: "1.5rem" }} aria-label="Recent sync activity">
        <SectionHeader title="Recent Sync Events" />
        <Card>
          <div style={{ overflowX: "auto", padding: "1rem" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.85rem" }}>
              <thead>
                <tr style={{ borderBottom: "2px solid #e2e8f0", color: "#475569" }}>
                  <th style={{ padding: "0.75rem 1rem" }}>Event ID</th>
                  <th style={{ padding: "0.75rem 1rem" }}>Node</th>
                  <th style={{ padding: "0.75rem 1rem" }}>Field Time</th>
                  <th style={{ padding: "0.75rem 1rem" }}>Gateway Time</th>
                  <th style={{ padding: "0.75rem 1rem" }}>Result</th>
                  <th style={{ padding: "0.75rem 1rem" }}>Verification</th>
                </tr>
              </thead>
              <tbody>
                {history.slice(0, 10).map((evt) => (
                  <tr key={evt.id} style={{ borderBottom: "1px solid #f1f5f9" }}>
                    <td style={{ padding: "0.6rem 1rem", fontWeight: 600, color: "var(--color-forest-dark)" }}>{evt.eventId}</td>
                    <td style={{ padding: "0.6rem 1rem" }}>{evt.nodeId}</td>
                    <td style={{ padding: "0.6rem 1rem" }}>{evt.eventTimestamp}</td>
                    <td style={{ padding: "0.6rem 1rem" }}>{evt.gatewayReceiveTime}</td>
                    <td style={{ padding: "0.6rem 1rem" }}>
                      <StatusBadge label={evt.syncResult} tone={evt.syncResult === "SUCCESS" ? "healthy" : "danger"} />
                    </td>
                    <td style={{ padding: "0.6rem 1rem" }}>
                      <StatusBadge label={evt.verificationResult} tone={evt.verificationResult === "PASSED" ? "healthy" : "danger"} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      </section>
    </div>
  );
}
