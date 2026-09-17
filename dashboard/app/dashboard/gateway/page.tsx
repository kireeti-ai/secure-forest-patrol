"use client";

import { useEffect, useRef, useState } from "react";
import { fetchGateways, GatewayStatus } from "../../../lib/api";
import { Card } from "../../../components/ui/Card";
import { SectionHeader } from "../../../components/ui/SectionHeader";
import { StatusBadge } from "../../../components/ui/StatusBadge";
import { useForestWebSocket } from "../../../lib/ws";

function LinkCard({ title, status, detail, tone }: { title: string; status: string; detail: string; tone: "healthy" | "warning" | "danger" }) {
  const colorMap = { healthy: "#16a34a", warning: "#d97706", danger: "#dc2626" };
  const bgMap = { healthy: "#f0fdf4", warning: "#fffbeb", danger: "#fef2f2" };
  const borderMap = { healthy: "#bbf7d0", warning: "#fde68a", danger: "#fecaca" };

  return (
    <div style={{ padding: "1.25rem", background: bgMap[tone], border: `1px solid ${borderMap[tone]}`, borderRadius: "10px", flex: 1 }}>
      <p style={{ fontSize: "0.8rem", fontWeight: 700, color: "#64748b", textTransform: "uppercase", letterSpacing: "0.05em" }}>{title}</p>
      <p style={{ fontSize: "1.8rem", fontWeight: 700, color: colorMap[tone], margin: "6px 0" }}>{status}</p>
      <p style={{ fontSize: "0.82rem", color: "#475569" }}>{detail}</p>
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
    <div className="dashboard-page" style={{ padding: "1.5rem" }}>
      <header className="page-header" style={{ marginBottom: "1.5rem", display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
        <div>
          <h1 style={{ fontSize: "1.75rem", fontWeight: 700, color: "var(--color-navy)" }}>
            Dual-Link Gateway Monitor
          </h1>
          <p style={{ color: "#64748b", marginTop: "4px" }}>
            The gateway bridges two separate network domains: a <strong>LoRa Field Link</strong> (Node → Gateway) over 433 MHz,
            and a <strong>Wi-Fi Backhaul IP Link</strong> (Gateway → Backend) over your local/cellular network.
          </p>
        </div>
        {gw?.isDemo && (
          <span style={{ padding: "6px 14px", borderRadius: "20px", background: "#fef3c7", color: "#92400e", border: "1px solid #fde68a", fontWeight: 700, fontSize: "0.8rem", whiteSpace: "nowrap" }}>
            DEMO / MOCK / NOT CONNECTED
          </span>
        )}
      </header>

      {/* ARCHITECTURE DIAGRAM */}
      <Card style={{ marginBottom: "1.5rem", padding: "1.25rem" }}>
        <h3 style={{ fontWeight: 700, color: "var(--color-navy)", marginBottom: "1rem" }}>Network Architecture</h3>
        <div style={{ display: "flex", alignItems: "center", gap: "1rem", flexWrap: "wrap", overflowX: "auto" }}>
          {[
            { label: "Field Nodes", sub: "Checkpoint / Acoustic", icon: "📡" },
            { label: "LoRa Field Link", sub: "433 MHz SX1278\nOffline-capable DTN", icon: null, isLink: true, color: "#2563eb" },
            { label: "ESP32-S3 Gateway", sub: `${gw?.gatewayId || "GW-FOREST-01"}\n${gw?.firmware || "v2.1.0"}`, icon: "🔁" },
            { label: "Wi-Fi Backhaul", sub: `IP: ${gw?.wifiIp || "—"}\nWPA2 Secured`, icon: null, isLink: true, color: "#0369a1" },
            { label: "Forest Backend", sub: "FastAPI\n+ PostgreSQL", icon: "☁️" },
          ].map((n, i) =>
            n.isLink ? (
              <div key={i} style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "4px" }}>
                <div style={{ width: "80px", height: "2px", background: n.color }} />
                <span style={{ fontSize: "0.75rem", color: n.color, fontWeight: 700 }}>{n.sub?.split("\n")[0]}</span>
                <span style={{ fontSize: "0.7rem", color: "#94a3b8" }}>{n.sub?.split("\n")[1]}</span>
              </div>
            ) : (
              <div key={i} style={{ textAlign: "center", padding: "12px 20px", background: "#f8fafc", border: "1px solid #e2e8f0", borderRadius: "10px" }}>
                <span style={{ fontSize: "1.5rem" }}>{n.icon}</span>
                <p style={{ fontWeight: 700, color: "#0f172a", marginTop: "4px" }}>{n.label}</p>
                {n.sub?.split("\n").map((s, j) => (
                  <p key={j} style={{ fontSize: "0.78rem", color: "#64748b", marginTop: "2px" }}>{s}</p>
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
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.9rem" }}>
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
                <tr key={String(label)} style={{ borderBottom: "1px solid #f1f5f9" }}>
                  <td style={{ padding: "10px 16px", fontWeight: 600, color: "#64748b", width: "220px" }}>{label}</td>
                  <td style={{ padding: "10px 16px", color: "#0f172a" }}>{value}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>

        <Card>
          <SectionHeader title="How Offline Sync Works" />
          <div style={{ padding: "1rem", fontSize: "0.88rem", color: "#475569", lineHeight: "1.7" }}>
            <ol style={{ paddingLeft: "1.2rem" }}>
              <li><strong>Field Event Created:</strong> Node signs and hashes patrol/acoustic event, stores in local queue.</li>
              <li><strong>LoRa Transmission:</strong> Node broadcasts over 433 MHz SX1278 — gateway does not need to be online at event time.</li>
              <li><strong>Gateway Receives:</strong> Gateway decodes, verifies signature, checks hash chain, deduplicates.</li>
              <li><strong>Wi-Fi Forward:</strong> Gateway forwards verified record to backend over Wi-Fi/IP backhaul.</li>
              <li><strong>Backend ACK:</strong> Backend stores in PostgreSQL and returns acknowledgement. Gateway marks as synced.</li>
            </ol>
            <p style={{ marginTop: "0.75rem", fontSize: "0.82rem", color: "#94a3b8" }}>
              If Wi-Fi is unavailable, records queue locally until connectivity is restored. The LoRa link is always separate from the Wi-Fi IP backhaul.
            </p>
          </div>
        </Card>
      </div>
    </div>
  );
}
