"use client";

import { useEffect, useRef, useState } from "react";
import { fetchGateways, GatewayStatus } from "../../../lib/api";
import { Card } from "../../../components/ui/Card";
import { SectionHeader } from "../../../components/ui/SectionHeader";
import { StatusBadge } from "../../../components/ui/StatusBadge";
import { useForestWebSocket } from "../../../lib/ws";

function NodeIcon({ kind }: { kind: "node" | "gateway" | "backend" }) {
  const common = { width: 26, height: 26, viewBox: "0 0 24 24", fill: "none", stroke: "var(--color-text)", strokeWidth: 1.7, strokeLinecap: "round" as const, strokeLinejoin: "round" as const, "aria-hidden": true };
  if (kind === "node") return <svg {...common}><circle cx="12" cy="12" r="2" /><path d="M7.8 7.8a6 6 0 0 0 0 8.4M16.2 7.8a6 6 0 0 1 0 8.4M4.9 4.9a10 10 0 0 0 0 14.2M19.1 4.9a10 10 0 0 1 0 14.2" /></svg>;
  if (kind === "gateway") return <svg {...common}><rect x="3" y="14" width="18" height="6" rx="1.5" /><path d="M7 17h.01M11 17h.01M8 10a6 6 0 0 1 8 0M5.5 7.5a10 10 0 0 1 13 0" /></svg>;
  return <svg {...common}><rect x="4" y="4" width="16" height="6" rx="1.5" /><rect x="4" y="14" width="16" height="6" rx="1.5" /><path d="M8 7h.01M8 17h.01" /></svg>;
}

function LinkCard({ title, status, detail, tone }: { title: string; status: string; detail: string; tone: "healthy" | "warning" | "danger" }) {
  const colorMap = { healthy: "var(--color-healthy)", warning: "var(--color-warning)", danger: "var(--color-danger)" };
  const bgMap = { healthy: "var(--color-healthy-bg)", warning: "var(--color-warning-bg)", danger: "var(--color-danger-bg)" };
  const borderMap = { healthy: "var(--color-border)", warning: "var(--color-border)", danger: "var(--color-border)" };

  return (
    <div style={{ padding: "1.25rem", background: bgMap[tone], border: `1px solid ${borderMap[tone]}`, borderRadius: "10px", flex: 1 }}>
      <p className="stat-label">{title}</p>
      <p style={{ fontSize: "1.8rem", fontWeight: 700, color: colorMap[tone], margin: "6px 0" }}>{status}</p>
      <p style={{ fontSize: "0.82rem", color: "var(--color-text-soft)" }}>{detail}</p>
    </div>
  );
}

export default function GatewayPage() {
  const [gw, setGw] = useState<GatewayStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const loadRef = useRef<() => void>(() => {});

  useEffect(() => {
    async function load() {
      const gateways = await fetchGateways();
      setGw(gateways[0] || null);
      setLoading(false);
    }
    loadRef.current = load;
    load();
    const interval = setInterval(load, 15000);
    return () => clearInterval(interval);
  }, []);

  useForestWebSocket(
    ["GATEWAY_STATUS_CHANGED", "SYNC_UPDATED"],
    () => loadRef.current(),
    () => loadRef.current()
  );

  return (
    <div className="dashboard-page">
      <header className="page-header" style={{ marginBottom: "1.5rem", display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
        <div>
          <h1>
            Gateway
          </h1>
          <p>Field nodes reach the gateway over LoRa (433 MHz); the gateway forwards to the backend over Wi-Fi using MQTT.</p>
        </div>
      </header>

      {/* ARCHITECTURE DIAGRAM */}
      <Card style={{ marginBottom: "1.5rem", padding: "1.25rem" }}>
        <h3 style={{ fontWeight: 700, color: "var(--color-navy)", marginBottom: "1rem" }}>Network Architecture</h3>
        <div style={{ display: "flex", alignItems: "center", gap: "1rem", flexWrap: "wrap", overflowX: "auto" }}>
          {[
            { label: "Field Nodes", sub: "Checkpoint / Acoustic", icon: "node" },
            { label: "LoRa Field Link", sub: "433 MHz SX1278\nLoRa", icon: null, isLink: true, color: "var(--color-forest-dark)" },
            { label: "ESP32-S3 Gateway", sub: `${gw?.gatewayId || "—"}\n${gw?.firmware || "—"}`, icon: "gateway" },
            { label: "Wi-Fi Backhaul", sub: `IP: ${gw?.wifiIp || "—"}\nMQTT`, icon: null, isLink: true, color: "var(--color-forest-dark)" },
            { label: "Forest Backend", sub: "FastAPI\n+ PostgreSQL", icon: "backend" },
          ].map((n, i) =>
            n.isLink ? (
              <div key={i} style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "4px" }}>
                <div style={{ width: "80px", height: "2px", background: n.color }} />
                <span style={{ fontSize: "0.75rem", color: n.color, fontWeight: 700 }}>{n.sub?.split("\n")[0]}</span>
                <span style={{ fontSize: "0.7rem", color: "var(--color-faint)" }}>{n.sub?.split("\n")[1]}</span>
              </div>
            ) : (
              <div key={i} style={{ textAlign: "center", padding: "12px 20px", background: "var(--color-surface-alt)", border: "1px solid var(--color-border)", borderRadius: "10px" }}>
                <NodeIcon kind={n.icon as "node" | "gateway" | "backend"} />
                <p style={{ fontWeight: 700, color: "var(--color-text)", marginTop: "4px" }}>{n.label}</p>
                {n.sub?.split("\n").map((s, j) => (
                  <p key={j} style={{ fontSize: "0.78rem", color: "var(--color-muted)", marginTop: "2px" }}>{s}</p>
                ))}
              </div>
            )
          )}
        </div>
      </Card>

      {/* DUAL LINK STATUS */}
      <div style={{ display: "flex", gap: "1rem", marginBottom: "1.5rem", flexWrap: "wrap" }}>
        <LinkCard
          title="LoRa Field Link"
          status={loading ? "..." : gw?.loraStatus || "UNKNOWN"}
          detail="SX1278 433 MHz — Receives encrypted event packets from field nodes. Works offline (DTN)."
          tone={!gw ? "warning" : gw.loraStatus === "ACTIVE" ? "healthy" : "warning"}
        />
        <LinkCard
          title="Wi-Fi Backhaul IP Link"
          status={loading ? "..." : gw?.wifiStatus || "UNKNOWN"}
          detail={`IP Address: ${gw?.wifiIp || "Not assigned"} — Forwards verified records to cloud/backend.`}
          tone={!gw ? "danger" : gw.wifiStatus === "CONNECTED" ? "healthy" : "danger"}
        />
        <LinkCard
          title="Backend API Reachability"
          status={loading ? "..." : gw?.backendStatus || "UNKNOWN"}
          detail="FastAPI Forest Service. Records are queued locally if unreachable (offline-first DTN)."
          tone={!gw ? "danger" : gw.backendStatus === "REACHABLE" ? "healthy" : "danger"}
        />
      </div>

      {/* STATISTICS */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1.5rem" }}>
        <Card>
          <SectionHeader title="Gateway Statistics" />
          <table>
            <tbody>
              {[
                ["Gateway ID", gw?.gatewayId || "—"],
                ["Firmware", gw?.firmware || "—"],
                ["Status", <StatusBadge key="s" label={gw?.status || "UNKNOWN"} tone={gw?.status === "ONLINE" ? "healthy" : "danger"} />],
                ["Records Received (LoRa)", gw?.recordsReceived ?? "—"],
                ["Records Forwarded (Wi-Fi)", gw?.recordsForwarded ?? "—"],
                ["Pending Sync Queue", gw?.pendingSyncQueue ?? "—"],
                ["Duplicate Packets Discarded", gw?.duplicatePackets ?? "—"],
                ["Verification Failures", gw?.verificationFailures ?? "—"],
              ].map(([label, value]) => (
                <tr key={String(label)}>
                  <td>{label}</td>
                  <td>{value}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>

      </div>
    </div>
  );
}
