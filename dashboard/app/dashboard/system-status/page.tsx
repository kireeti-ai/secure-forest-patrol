"use client";

import { useEffect, useState } from "react";
import { fetchForestSystemStatus, ForestSystemStatus } from "../../../lib/api";
import { Card } from "../../../components/ui/Card";

type ComponentStatus = "OPERATIONAL" | "CONNECTED" | "REACHABLE" | "HEALTHY" | "DEGRADED" | "OFFLINE";

const statusColors: Record<ComponentStatus, { bg: string; border: string; text: string; dot: string }> = {
  OPERATIONAL: { bg: "var(--color-healthy-bg)", border: "var(--color-border)", text: "var(--color-healthy)", dot: "var(--color-healthy)" },
  CONNECTED:   { bg: "var(--color-healthy-bg)", border: "var(--color-border)", text: "var(--color-healthy)", dot: "var(--color-healthy)" },
  REACHABLE:   { bg: "var(--color-healthy-bg)", border: "var(--color-border)", text: "var(--color-healthy)", dot: "var(--color-healthy)" },
  HEALTHY:     { bg: "var(--color-healthy-bg)", border: "var(--color-border)", text: "var(--color-healthy)", dot: "var(--color-healthy)" },
  DEGRADED:    { bg: "var(--color-warning-bg)", border: "var(--color-border)", text: "var(--color-warning)", dot: "var(--color-warning)" },
  OFFLINE:     { bg: "var(--color-danger-bg)", border: "var(--color-border)", text: "var(--color-danger)", dot: "var(--color-danger)" },
};

function ComponentRow({ label, status, details }: { label: string; status: ComponentStatus; details: string }) {
  const c = statusColors[status] || statusColors.DEGRADED;
  return (
    <div style={{ padding: "1rem 1.25rem", background: c.bg, border: `1px solid ${c.border}`, borderRadius: "8px", display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "0.5rem" }}>
      <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
        <span style={{ width: "10px", height: "10px", borderRadius: "50%", background: c.dot, boxShadow: status !== "OFFLINE" && status !== "DEGRADED" ? `0 0 8px ${c.dot}` : "none", display: "inline-block", flexShrink: 0 }} />
        <div>
          <strong style={{ color: "var(--color-text)" }}>{label}</strong>
          <p style={{ fontSize: "0.82rem", color: "var(--color-muted)", marginTop: "2px" }}>{details}</p>
        </div>
      </div>
      <span style={{ fontWeight: 700, fontSize: "0.85rem", color: c.text, background: "rgba(255,255,255,0.6)", padding: "4px 12px", borderRadius: "16px", border: `1px solid ${c.border}` }}>
        {status}
      </span>
    </div>
  );
}

export default function SystemStatusPage() {
  const [status, setStatus] = useState<ForestSystemStatus | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      const data = await fetchForestSystemStatus();
      setStatus(data);
      setLoading(false);
    }
    load();
    const interval = setInterval(load, 10000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="dashboard-page">
      <header className="page-header" style={{ marginBottom: "1.5rem", display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
        <div>
          <h1>System status</h1>
          <p style={{ color: "var(--color-muted)", marginTop: "4px" }}>
            Health overview of all system layers: field nodes, LoRa field link, Wi-Fi backhaul, backend, database, and ledger verification.
          </p>
        </div>
      </header>

      {loading ? (
        <p>Loading system status...</p>
      ) : status ? (
        <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
          <ComponentRow label={status.fieldLayer.component} status={status.fieldLayer.status as ComponentStatus} details={status.fieldLayer.details} />
          <ComponentRow label={status.gateway.component} status={status.gateway.status as ComponentStatus} details={status.gateway.details} />
          <ComponentRow label={status.wifiBackhaul.component} status={status.wifiBackhaul.status as ComponentStatus} details={status.wifiBackhaul.details} />
          <ComponentRow label={status.backend.component} status={status.backend.status as ComponentStatus} details={status.backend.details} />
          <ComponentRow label={status.database.component} status={status.database.status as ComponentStatus} details={status.database.details} />
          <ComponentRow label={status.ledgerVerification.component} status={status.ledgerVerification.status as ComponentStatus} details={status.ledgerVerification.details} />
        </div>
      ) : (
        <p style={{ color: "var(--color-danger)" }}>Unable to fetch system status.</p>
      )}

      <Card style={{ marginTop: "1.5rem", padding: "1.25rem" }}>
        <h3 style={{ fontWeight: 700, color: "var(--color-navy)", marginBottom: "1rem" }}>Architecture Overview</h3>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem", fontSize: "0.88rem", color: "var(--color-text-soft)" }}>
          <div>
            <h4 style={{ color: "var(--color-text)", marginBottom: "0.5rem" }}>Field Layer</h4>
            <ul style={{ paddingLeft: "1.2rem", lineHeight: "1.7" }}>
              <li>ESP32-based Field Nodes (Checkpoint + Acoustic)</li>
              <li>SX1278 LoRa 433 MHz transceiver</li>
              <li>TinyML on-device acoustic classification</li>
              <li>DS3231 RTC for offline timestamping</li>
              <li>RSA signing + SHA-256 hash chain on-node</li>
            </ul>
          </div>
          <div>
            <h4 style={{ color: "var(--color-text)", marginBottom: "0.5rem" }}>Network & Backend Layer</h4>
            <ul style={{ paddingLeft: "1.2rem", lineHeight: "1.7" }}>
              <li>ESP32-S3 Gateway — LoRa + Wi-Fi dual mode</li>
              <li>DTN offline-first synchronization queue</li>
              <li>FastAPI Forest Backend (Python)</li>
              <li>PostgreSQL + hash chain verification engine</li>
              <li>Duplicate detection and RSA verification at gateway</li>
            </ul>
          </div>
        </div>
      </Card>
    </div>
  );
}
