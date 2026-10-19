"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import {
  fetchCheckpoints,
  fetchAcousticEvents,
  fetchGateways,
  fetchNodes,
  Checkpoint,
  AcousticEvent,
  GatewayStatus,
  FieldNode,
} from "../../lib/api";
import { Card } from "../ui/Card";
import { SectionHeader } from "../ui/SectionHeader";
import { StatusBadge } from "../ui/StatusBadge";
import { fetchRfidEvents, fetchVerificationEvents, type RfidEvent, type VerificationEvent } from "../../lib/rfidApi";
import { useForestWebSocket } from "../../lib/ws";

const OVERVIEW_WS_EVENTS = [
  "ACOUSTIC_EVENT_RECEIVED",
  "NODE_STATUS_CHANGED",
  "GATEWAY_STATUS_CHANGED",
  "SYNC_UPDATED",
  "RFID_SCAN_RECEIVED",
  "VERIFICATION_RECEIVED",
] as const;

function scanTone(status: string): "healthy" | "warning" | "danger" {
  return status === "AUTHORIZED" ? "healthy" : status === "UNKNOWN" ? "warning" : "danger";
}

function Metric({
  label,
  value,
  supportingText,
  tone = "normal",
}: {
  label: string;
  value: string | number;
  supportingText: string;
  tone?: "normal" | "healthy" | "warning" | "danger";
}) {
  const toneColors = {
    normal: "var(--color-forest-dark)",
    healthy: "var(--color-healthy)",
    warning: "var(--color-warning)",
    danger: "var(--color-danger)",
  };

  return (
    <Card className="overview-metric" style={{ }}>
      <p className="overview-metric-label">{label}</p>
      <p className="overview-metric-value" style={{ color: toneColors[tone] }}>
        {value}
      </p>
      <p className="overview-metric-supporting">{supportingText}</p>
    </Card>
  );
}

export function Overview() {
  const [checkpoints, setCheckpoints] = useState<Checkpoint[]>([]);
  const [verifications, setVerifications] = useState<VerificationEvent[]>([]);
  const [acoustics, setAcoustics] = useState<AcousticEvent[]>([]);
  const [gateways, setGateways] = useState<GatewayStatus[]>([]);
  const [nodes, setNodes] = useState<FieldNode[]>([]);
  const [loading, setLoading] = useState(true);
  const [rfidScans, setRfidScans] = useState<RfidEvent[]>([]);

  const loadDataRef = useRef<() => void>(() => {});

  useEffect(() => {
    let mounted = true;

    async function loadData() {
      const [cpData, verData, acData, gwData, nodeData, rfidData] = await Promise.all([
        fetchCheckpoints(),
        fetchVerificationEvents().catch(() => [] as VerificationEvent[]),
        fetchAcousticEvents(),
        fetchGateways(),
        fetchNodes(),
        fetchRfidEvents().catch(() => [] as RfidEvent[]),
      ]);
      if (!mounted) return;
      setCheckpoints(cpData);
      setVerifications(verData);
      setAcoustics(acData);
      setGateways(gwData);
      setNodes(nodeData);
      setRfidScans(rfidData.slice(0, 10));
      setLoading(false);
    }

    loadDataRef.current = loadData;
    loadData();
    // Falls back to polling if the WebSocket below is down; live events
    // trigger an immediate refetch on top of this.
    const interval = setInterval(loadData, 15000);
    return () => {
      mounted = false;
      clearInterval(interval);
    };
  }, []);

  useForestWebSocket(
    [...OVERVIEW_WS_EVENTS],
    () => loadDataRef.current(),
    () => loadDataRef.current()
  );

  const activeCheckpoints = checkpoints.filter((c) => c.state === "ONLINE").length;
  const verifiedVisits = verifications.filter((v) => v.status === "MATCH").length;
  const proxyAttempts = verifications.filter((v) => v.status === "MISMATCH").length;
  const pendingAcousticReviews = acoustics.filter((a) => a.reviewStatus === "PENDING_REVIEW").length;
  const pendingSyncCount = checkpoints.reduce((acc, c) => acc + c.pendingRecords, 0);

  const gw = gateways[0];
  const RECENT_MS = 2 * 60 * 1000;
  const gatewayFresh = !!gw?.lastSeen && Date.now() - new Date(gw.lastSeen).getTime() <= RECENT_MS;
  const liveCheckpoint = checkpoints.find((c) => c.state === "ONLINE");
  const isLoraConnected = gatewayFresh && !!liveCheckpoint;
  // Link badges show only what the gateway last reported. No gateway data -> NO DATA;
  // a gateway that has stopped reporting -> OFFLINE. Never a made-up healthy value.
  const linkLabel = (reported?: string) => (!gw ? "NO DATA" : gatewayFresh ? reported ?? "UNKNOWN" : "OFFLINE");
  const linkTone = (reported: string | undefined, healthy: string): "healthy" | "warning" | "danger" =>
    !gw ? "warning" : gatewayFresh && reported === healthy ? "healthy" : "danger";

  return (
    <div className="overview-page">
      <header className="overview-header" style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
        <div>
          <h1>Overview</h1>
          <p style={{ color: "var(--color-muted)", marginTop: "4px" }}>
            Real-time status of checkpoint verification, acoustic threat monitoring, and dual-link gateway backhaul.
          </p>
        </div>
      </header>

      {isLoraConnected && (
        <Card style={{ marginTop: "1.25rem", padding: "1rem 1.25rem", background: "var(--color-healthy-bg)", border: "1px solid var(--color-border)" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: "1rem", flexWrap: "wrap" }}>
            <div>
              <strong style={{ color: "var(--color-healthy)", fontSize: "0.96rem" }}>Field node and gateway are active.</strong>
              <p style={{ color: "var(--color-healthy)", fontSize: "0.82rem", margin: "4px 0 0" }}>
                {`${gw?.gatewayId ?? "Gateway"} last reported ${new Date(gw!.lastSeen).toLocaleTimeString()} · ${liveCheckpoint!.nodeId} (${liveCheckpoint!.checkpointId}) last scan ${liveCheckpoint!.lastPatrolTime}`}
              </p>
            </div>
            <StatusBadge label="LORa ONLINE" tone="healthy" />
          </div>
        </Card>
      )}

      {/* METRICS GRID */}
      <section className="overview-section" style={{ marginTop: "1.5rem" }}>
        <div className="overview-metrics">
          <Metric
            label="ACTIVE CHECKPOINTS"
            value={loading ? "..." : `${activeCheckpoints}/${checkpoints.length}`}
            supportingText={`${activeCheckpoints} nodes online`}
            tone="healthy"
          />
          <Metric
            label="VERIFIED VISITS"
            value={loading ? "..." : verifiedVisits}
            supportingText={`${verifications.length} total checkpoint verifications`}
            tone="healthy"
          />
          <Metric
            label="PROXY ATTEMPTS"
            value={loading ? "..." : proxyAttempts}
            supportingText={proxyAttempts > 0 ? "Card tapped, fingerprint did not match -- review" : "Zero mismatches"}
            tone={proxyAttempts > 0 ? "danger" : "healthy"}
          />
          <Metric
            label="ACOUSTIC QUEUE"
            value={loading ? "..." : pendingAcousticReviews}
            supportingText={pendingAcousticReviews > 0 ? `${pendingAcousticReviews} pending review` : "Review queue clear"}
            tone={pendingAcousticReviews > 0 ? "warning" : "healthy"}
          />
          <Metric
            label="PENDING SYNC"
            value={loading ? "..." : pendingSyncCount}
            supportingText={pendingSyncCount > 0 ? `${pendingSyncCount} records in DTN queue` : "All records synchronized"}
            tone={pendingSyncCount > 0 ? "warning" : "healthy"}
          />
        </div>
      </section>

      {/* GATEWAY DUAL LINK BANNER */}
      <Card style={{ marginTop: "1.5rem", padding: "1.25rem", background: "var(--color-surface-alt)", border: "1px solid var(--color-border)" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "1rem" }}>
          <div>
            <h3 style={{ fontSize: "1.1rem", fontWeight: 700, color: "var(--color-forest-dark)" }}>
              Gateway Backhaul: {gw?.gatewayId ?? "no gateway reported"}
            </h3>
            <p style={{ fontSize: "0.85rem", color: "var(--color-muted)", marginTop: "2px" }}>
              LoRa field link receives offline events from nodes. Wi-Fi backhaul forwards verified records to cloud backend.
            </p>
          </div>
          <div style={{ display: "flex", gap: "1.5rem", alignItems: "center" }}>
            <div style={{ textAlign: "center" }}>
              <span style={{ fontSize: "0.75rem", color: "var(--color-muted)", fontWeight: 600, display: "block" }}>LoRa Field Link</span>
              <StatusBadge label={linkLabel(gw?.loraStatus)} tone={linkTone(gw?.loraStatus, "ACTIVE")} />
            </div>
            <div style={{ textAlign: "center" }}>
              <span style={{ fontSize: "0.75rem", color: "var(--color-muted)", fontWeight: 600, display: "block" }}>Wi-Fi Backhaul</span>
              <StatusBadge label={linkLabel(gw?.wifiStatus)} tone={linkTone(gw?.wifiStatus, "CONNECTED")} />
            </div>
            <div style={{ textAlign: "center" }}>
              <span style={{ fontSize: "0.75rem", color: "var(--color-muted)", fontWeight: 600, display: "block" }}>Backend API</span>
              <StatusBadge label={linkLabel(gw?.backendStatus)} tone={linkTone(gw?.backendStatus, "REACHABLE")} />
            </div>
            <Link
              href="/dashboard/gateway"
              style={{
                padding: "6px 14px",
                fontSize: "0.8rem",
                fontWeight: 600,
                color: "var(--color-forest-dark)",
                border: "1px solid var(--color-border)",
                borderRadius: "6px",
                background: "var(--color-surface-alt)",
                textDecoration: "none",
              }}
            >
              Gateway Details →
            </Link>
          </div>
        </div>
      </Card>

      {/* TWO COLUMN PANELS */}
      <div style={{ display: "grid", gridTemplateColumns: "1.2fr 0.8fr", gap: "1.5rem", marginTop: "1.5rem" }}>
        {/* RECENT PATROLS & VERIFICATION */}
        <Card>
          <SectionHeader title="Recent Checkpoint Verifications" />
          <div style={{ padding: "1rem" }}>
            {verifications.length === 0 ? (
              <div className="overview-empty-state">
                <p className="overview-empty-title">No verification events logged</p>
              </div>
            ) : (
              <table>
                <thead>
                  <tr>
                    <th>Time</th>
                    <th>Checkpoint</th>
                    <th>Officer</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {verifications.slice(0, 5).map((v) => (
                    <tr key={v.id}>
                      <td>{new Date(v.timestamp).toLocaleTimeString()}</td>
                      <td>
                        <strong>{v.checkpoint_id ?? "—"}</strong> ({v.node_id})
                      </td>
                      <td>{v.claimed_name ?? v.claimed_employee_id ?? v.claimed_uid}</td>
                      <td>
                        <StatusBadge label={v.status} tone={v.status === "MATCH" ? "healthy" : v.status === "MISMATCH" ? "danger" : "warning"} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
            <div style={{ marginTop: "1rem", textAlign: "right" }}>
              <Link href="/dashboard/officers" style={{ fontSize: "0.85rem", color: "var(--color-forest-dark)", fontWeight: 600 }}>
                View Officers →
              </Link>
            </div>
          </div>
        </Card>

        {/* ACOUSTIC THREAT QUEUE SUMMARY */}
        <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
          <Card>
            <SectionHeader title="Acoustic events awaiting review" />
            <div style={{ padding: "1rem" }}>
              {acoustics.length === 0 ? (
                <div className="overview-empty-state">
                  <p className="overview-empty-title">Queue Clear</p>
                </div>
              ) : (
                acoustics.slice(0, 4).map((a) => (
                  <div
                    key={a.id}
                    style={{
                      padding: "0.75rem",
                      borderRadius: "6px",
                      marginBottom: "0.5rem",
                      background: a.classification === "Gunshot" ? "var(--color-danger-bg)" : a.classification === "Chainsaw" ? "var(--color-warning-bg)" : "var(--color-surface-alt)",
                      border: "1px solid " + (a.classification === "Gunshot" ? "var(--color-border)" : a.classification === "Chainsaw" ? "var(--color-warning-bg)" : "var(--color-border)"),
                    }}
                  >
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                      <strong style={{ color: a.classification === "Gunshot" ? "var(--color-danger)" : a.classification === "Chainsaw" ? "var(--color-warning)" : "var(--color-text)" }}>
                        {a.classification} ({Math.round(a.confidence * 100)}%)
                      </strong>
                      <StatusBadge
                        label={a.reviewStatus}
                        tone={a.reviewStatus === "CONFIRMED" ? "danger" : a.reviewStatus === "PENDING_REVIEW" ? "warning" : "healthy"}
                      />
                    </div>
                    <div style={{ fontSize: "0.8rem", color: "var(--color-muted)", marginTop: "4px", display: "flex", justifyContent: "space-between" }}>
                      <span>
                        Node {a.nodeId} • {a.zone}
                      </span>
                      <span>{a.timestamp.split(" ")[1] || a.timestamp}</span>
                    </div>
                  </div>
                ))
              )}
              <div style={{ marginTop: "1rem", textAlign: "right" }}>
                <Link href="/dashboard/acoustic-events" style={{ fontSize: "0.85rem", color: "var(--color-forest-dark)", fontWeight: 600 }}>
                  Open Threat Review Queue →
                </Link>
              </div>
            </div>
          </Card>

          {/* FIELD NODES SUMMARY */}
          <Card>
            <SectionHeader title="Field nodes" />
            <div style={{ padding: "1rem" }}>
              {nodes.map((n) => (
                <div key={n.id} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "6px 0", borderBottom: "1px solid var(--color-surface-alt)" }}>
                  <div>
                    <strong style={{ fontSize: "0.9rem" }}>{n.nodeId}</strong>
                    <span style={{ fontSize: "0.8rem", color: "var(--color-muted)", marginLeft: "6px" }}>({n.nodeType})</span>
                  </div>
                  <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
                    <span style={{ fontSize: "0.8rem", color: "var(--color-muted)" }}>Batt: {n.batteryLevel ?? "—"}%</span>
                    <StatusBadge label={n.health ?? "UNKNOWN"} tone={n.health === "HEALTHY" ? "healthy" : "warning"} />
                  </div>
                </div>
              ))}
            </div>
          </Card>
        </div>
      </div>

      {/* RFID SYSTEM */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 2fr", gap: "1.5rem", marginTop: "1.5rem" }}>
        <Card>
          <SectionHeader title="Latest RFID Scan" />
          <div style={{ padding: "1rem" }}>
            {rfidScans.length === 0 ? (
              <div className="overview-empty-state">
                <p className="overview-empty-title">Waiting for RFID scan...</p>
              </div>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: "8px", fontSize: "0.9rem" }}>
                <div style={{ display: "flex", justifyContent: "space-between" }}>
                  <span style={{ color: "var(--color-muted)" }}>RFID UID</span>
                  <strong>{rfidScans[0].uid}</strong>
                </div>
                <div style={{ display: "flex", justifyContent: "space-between" }}>
                  <span style={{ color: "var(--color-muted)" }}>Node</span>
                  <strong>{rfidScans[0].node_id}</strong>
                </div>
                <div style={{ display: "flex", justifyContent: "space-between" }}>
                  <span style={{ color: "var(--color-muted)" }}>Status</span>
                  <StatusBadge label={rfidScans[0].status} tone={scanTone(rfidScans[0].status)} />
                </div>
                <div style={{ display: "flex", justifyContent: "space-between" }}>
                  <span style={{ color: "var(--color-muted)" }}>RSSI</span>
                  <strong>{rfidScans[0].rssi} dBm</strong>
                </div>
                <div style={{ display: "flex", justifyContent: "space-between" }}>
                  <span style={{ color: "var(--color-muted)" }}>SNR</span>
                  <strong>{rfidScans[0].snr} dB</strong>
                </div>
                <div style={{ display: "flex", justifyContent: "space-between" }}>
                  <span style={{ color: "var(--color-muted)" }}>Time</span>
                  <strong>{new Date(rfidScans[0].timestamp).toLocaleTimeString()}</strong>
                </div>
              </div>
            )}
          </div>
        </Card>

        <Card>
          <SectionHeader title="RFID Event Table" />
          <div style={{ padding: "1rem" }}>
            {rfidScans.length === 0 ? (
              <div className="overview-empty-state">
                <p className="overview-empty-title">No events</p>
              </div>
            ) : (
              <table>
                <thead>
                  <tr>
                    <th>Time</th>
                    <th>Node</th>
                    <th>Checkpoint</th>
                    <th>Employee</th>
                    <th>RFID UID</th>
                    <th>RSSI</th>
                    <th>SNR</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {rfidScans.map((scan) => (
                    <tr key={scan.id}>
                      <td>
                        {new Date(scan.timestamp).toLocaleTimeString()}
                      </td>
                      <td>{scan.node_id}</td>
                      <td>{scan.checkpoint_id ?? "—"}</td>
                      <td>{scan.employee_id ?? "Unknown"}</td>
                      <td><strong>{scan.uid}</strong></td>
                      <td>{scan.rssi}</td>
                      <td>{scan.snr}</td>
                      <td title={scan.reason ?? undefined}><StatusBadge label={scan.status} tone={scanTone(scan.status)} />{scan.reason && <div style={{ fontSize: "0.72rem", color: "var(--color-danger)", marginTop: 2 }}>{scan.reason}</div>}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </Card>
      </div>
    </div>
  );
}
