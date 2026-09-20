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
        <p>LoRa link from the field nodes and the Wi-Fi/MQTT link to the backend.</p>
      </header>

      <section className="gateway-status-section" aria-label="Gateway status">
        <SectionHeader title="Gateway Connection" />
        <Card className="gateway-status-panel">
          <div className="gateway-status-content" style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <div>
              <p className="gateway-status-title" style={{ fontSize: "1.1rem", fontWeight: 600 }}>
                {gateway ? `Forest Gateway (${gateway.gatewayId})` : "Gateway unavailable"}
              </p>
              <p className="gateway-status-message" style={{ color: "var(--color-faint)", fontSize: "0.9rem" }}>
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
            <table>
              <thead>
                <tr>
                  <th>Event ID</th>
                  <th>Node</th>
                  <th>Field Time</th>
                  <th>Gateway Time</th>
                  <th>Result</th>
                  <th>Verification</th>
                </tr>
              </thead>
              <tbody>
                {history.slice(0, 10).map((evt) => (
                  <tr key={evt.id}>
                    <td>{evt.eventId}</td>
                    <td>{evt.nodeId}</td>
                    <td>{evt.eventTimestamp}</td>
                    <td>{evt.gatewayReceiveTime}</td>
                    <td>
                      <StatusBadge label={evt.syncResult} tone={evt.syncResult === "SUCCESS" ? "healthy" : "danger"} />
                    </td>
                    <td>
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
