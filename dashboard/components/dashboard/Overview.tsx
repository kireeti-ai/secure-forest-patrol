"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import {
  fetchCheckpoints,
  fetchPatrols,
  fetchAcousticEvents,
  fetchLedger,
  fetchGateways,
  fetchNodes,
  Checkpoint,
  PatrolRecord,
  AcousticEvent,
  LedgerRecord,
  GatewayStatus,
  FieldNode,
} from "../../lib/api";
import { Card } from "../ui/Card";
import { SectionHeader } from "../ui/SectionHeader";
import { StatusBadge } from "../ui/StatusBadge";
import { fetchRfidEvents, type RfidEvent } from "../../lib/rfidApi";
import { useForestWebSocket } from "../../lib/ws";

const OVERVIEW_WS_EVENTS = [
  "PATROL_EVENT_VERIFIED",
  "PATROL_EVENT_REJECTED",
  "ACOUSTIC_EVENT_RECEIVED",
  "LEDGER_VERIFICATION_RESULT",
  "NODE_STATUS_CHANGED",
  "GATEWAY_STATUS_CHANGED",
  "SYNC_UPDATED",
  "RFID_SCAN_RECEIVED",
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
    healthy: "#16a34a",
    warning: "#d97706",
    danger: "#dc2626",
  };

  return (
    <Card className="overview-metric" style={{ borderLeft: `4px solid ${toneColors[tone]}` }}>
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
  const [patrols, setPatrols] = useState<PatrolRecord[]>([]);
  const [acoustics, setAcoustics] = useState<AcousticEvent[]>([]);
  const [ledger, setLedger] = useState<LedgerRecord[]>([]);
  const [gateways, setGateways] = useState<GatewayStatus[]>([]);
  const [nodes, setNodes] = useState<FieldNode[]>([]);
  const [loading, setLoading] = useState(true);
  const [rfidScans, setRfidScans] = useState<RfidEvent[]>([]);

  const loadDataRef = useRef<() => void>(() => {});

  useEffect(() => {
    let mounted = true;

    async function loadData() {
      const [cpData, patData, acData, ledData, gwData, nodeData, rfidData] = await Promise.all([
        fetchCheckpoints(),
        fetchPatrols(),
        fetchAcousticEvents(),
        fetchLedger(),
        fetchGateways(),
        fetchNodes(),
        fetchRfidEvents().catch(() => [] as RfidEvent[]),
      ]);
      if (!mounted) return;
      setCheckpoints(cpData);
      setPatrols(patData);
      setAcoustics(acData);
      setLedger(ledData);
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
  const verifiedPatrols = patrols.filter((p) => p.rfidStatus === "VALID" && p.fingerprintStatus === "MATCH").length;
  const identityMismatches = patrols.filter((p) => p.fingerprintStatus === "NO_MATCH" || p.rfidStatus === "INVALID").length;
  const pendingAcousticReviews = acoustics.filter((a) => a.reviewStatus === "PENDING_REVIEW").length;
  const validLedgerRecords = ledger.filter((l) => l.chainStatus === "VALID").length;
  const ledgerFailures = ledger.filter((l) => l.chainStatus === "BROKEN" || l.signatureStatus === "INVALID").length;
  const pendingSyncCount = patrols.filter((p) => p.syncStatus === "PENDING").length + checkpoints.reduce((acc, c) => acc + c.pendingRecords, 0);

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
          <h1 style={{ fontSize: "1.75rem", fontWeight: 700, color: "var(--color-forest-dark)" }}>Forest Operations Overview</h1>
          <p style={{ color: "#64748b", marginTop: "4px" }}>
            Real-time status of patrol verification, acoustic threat monitoring, ledger integrity, and dual-link gateway backhaul.
          </p>
        </div>
      </header>

      {isLoraConnected && (
        <Card style={{ marginTop: "1.25rem", padding: "1rem 1.25rem", background: "#ecfdf5", border: "1px solid #bbf7d0" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: "1rem", flexWrap: "wrap" }}>
            <div>
              <strong style={{ color: "#166534", fontSize: "0.96rem" }}>Field node and gateway are active.</strong>
              <p style={{ color: "#166534", fontSize: "0.82rem", margin: "4px 0 0" }}>
                {`${gw?.gatewayId ?? "Gateway"} last reported ${new Date(gw!.lastSeen).toLocaleTimeString()} · ${liveCheckpoint!.nodeId} (${liveCheckpoint!.checkpointId}) last scan ${liveCheckpoint!.lastPatrolTime}`}
              </p>
            </div>
            <StatusBadge label="LORa ONLINE" tone="healthy" />
          </div>
        </Card>
      )}

      {/* METRICS GRID */}
      <section className="overview-section" style={{ marginTop: "1.5rem" }}>
        <div className="overview-metrics" style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "1rem" }}>
          <Metric
            label="ACTIVE CHECKPOINTS"
            value={loading ? "..." : `${activeCheckpoints}/${checkpoints.length}`}
            supportingText={`${activeCheckpoints} nodes online`}
            tone="healthy"
          />
          <Metric
            label="VERIFIED PATROLS"
            value={loading ? "..." : verifiedPatrols}
            supportingText={`${patrols.length} total events logged`}
            tone="healthy"
          />
          <Metric
            label="IDENTITY MISMATCHES"
            value={loading ? "..." : identityMismatches}
            supportingText={identityMismatches > 0 ? "Requires verification review" : "Zero mismatches"}
            tone={identityMismatches > 0 ? "danger" : "healthy"}
          />
          <Metric
            label="ACOUSTIC QUEUE"
            value={loading ? "..." : pendingAcousticReviews}
            supportingText={pendingAcousticReviews > 0 ? `${pendingAcousticReviews} pending review` : "Review queue clear"}
            tone={pendingAcousticReviews > 0 ? "warning" : "healthy"}
          />
          <Metric
            label="VALID LEDGER RECORDS"
            value={loading ? "..." : `${validLedgerRecords}/${ledger.length}`}
            supportingText={ledgerFailures > 0 ? `${ledgerFailures} broken chain records` : "Tamper-evident chain valid"}
            tone={ledgerFailures > 0 ? "danger" : "healthy"}
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
      <Card style={{ marginTop: "1.5rem", padding: "1.25rem", background: "#f8fafc", border: "1px solid #e2e8f0" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "1rem" }}>
          <div>
            <h3 style={{ fontSize: "1.1rem", fontWeight: 700, color: "var(--color-forest-dark)" }}>
              Gateway Backhaul: {gw?.gatewayId ?? "no gateway reported"}
            </h3>
            <p style={{ fontSize: "0.85rem", color: "#64748b", marginTop: "2px" }}>
              LoRa field link receives offline events from nodes. Wi-Fi backhaul forwards verified records to cloud backend.
            </p>
          </div>
          <div style={{ display: "flex", gap: "1.5rem", alignItems: "center" }}>
            <div style={{ textAlign: "center" }}>
              <span style={{ fontSize: "0.75rem", color: "#64748b", fontWeight: 600, display: "block" }}>LoRa Field Link</span>
              <StatusBadge label={linkLabel(gw?.loraStatus)} tone={linkTone(gw?.loraStatus, "ACTIVE")} />
            </div>
            <div style={{ textAlign: "center" }}>
              <span style={{ fontSize: "0.75rem", color: "#64748b", fontWeight: 600, display: "block" }}>Wi-Fi Backhaul</span>
              <StatusBadge label={linkLabel(gw?.wifiStatus)} tone={linkTone(gw?.wifiStatus, "CONNECTED")} />
            </div>
            <div style={{ textAlign: "center" }}>
              <span style={{ fontSize: "0.75rem", color: "#64748b", fontWeight: 600, display: "block" }}>Backend API</span>
              <StatusBadge label={linkLabel(gw?.backendStatus)} tone={linkTone(gw?.backendStatus, "REACHABLE")} />
            </div>
            <Link
              href="/dashboard/gateway"
              style={{
                padding: "6px 14px",
                fontSize: "0.8rem",
                fontWeight: 600,
                color: "#0369a1",
                border: "1px solid #bae6fd",
                borderRadius: "6px",
                background: "#f0f9ff",
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
          <SectionHeader title="Recent Patrol Events" />
          <div style={{ padding: "1rem" }}>
            {patrols.length === 0 ? (
              <div className="overview-empty-state">
                <p className="overview-empty-title">No patrol events logged</p>
              </div>
            ) : (
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.85rem" }}>
                <thead>
                  <tr style={{ borderBottom: "1px solid #e2e8f0", textAlign: "left", color: "#64748b" }}>
                    <th style={{ padding: "8px" }}>Time</th>
                    <th style={{ padding: "8px" }}>Checkpoint</th>
                    <th style={{ padding: "8px" }}>Officer</th>
                    <th style={{ padding: "8px" }}>RFID</th>
                    <th style={{ padding: "8px" }}>Biometric</th>
                    <th style={{ padding: "8px" }}>Ledger</th>
                  </tr>
                </thead>
                <tbody>
                  {patrols.slice(0, 5).map((p) => (
                    <tr key={p.id} style={{ borderBottom: "1px solid #f1f5f9" }}>
                      <td style={{ padding: "8px", fontWeight: 500 }}>{p.timestamp.split(" ")[1] || p.timestamp}</td>
                      <td style={{ padding: "8px" }}>
                        <strong>{p.checkpointId}</strong> ({p.nodeId})
                      </td>
                      <td style={{ padding: "8px" }}>{p.officerName}</td>
                      <td style={{ padding: "8px" }}>
                        <StatusBadge label={p.rfidStatus} tone={p.rfidStatus === "VALID" ? "healthy" : "danger"} />
                      </td>
                      <td style={{ padding: "8px" }}>
                        <StatusBadge label={p.fingerprintStatus} tone={p.fingerprintStatus === "MATCH" ? "healthy" : "danger"} />
                      </td>
                      <td style={{ padding: "8px" }}>
                        <StatusBadge label={p.ledgerStatus} tone={p.ledgerStatus === "VALID" ? "healthy" : "danger"} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
            <div style={{ marginTop: "1rem", textAlign: "right" }}>
              <Link href="/dashboard/patrols" style={{ fontSize: "0.85rem", color: "var(--color-forest-dark)", fontWeight: 600 }}>
                View All Patrol Events →
              </Link>
            </div>
          </div>
        </Card>

        {/* ACOUSTIC THREAT QUEUE SUMMARY */}
        <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
          <Card>
            <SectionHeader title="Acoustic Threat Review Queue" />
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
                      background: a.classification === "Gunshot" ? "#fef2f2" : a.classification === "Chainsaw" ? "#fffbeb" : "#f8fafc",
                      border: "1px solid " + (a.classification === "Gunshot" ? "#fecaca" : a.classification === "Chainsaw" ? "#fef3c7" : "#e2e8f0"),
                    }}
                  >
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                      <strong style={{ color: a.classification === "Gunshot" ? "#991b1b" : a.classification === "Chainsaw" ? "#92400e" : "#334155" }}>
                        {a.classification} ({Math.round(a.confidence * 100)}%)
                      </strong>
                      <StatusBadge
                        label={a.reviewStatus}
                        tone={a.reviewStatus === "CONFIRMED" ? "danger" : a.reviewStatus === "PENDING_REVIEW" ? "warning" : "healthy"}
                      />
                    </div>
                    <div style={{ fontSize: "0.8rem", color: "#64748b", marginTop: "4px", display: "flex", justifyContent: "space-between" }}>
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
            <SectionHeader title="Field Node Health" />
            <div style={{ padding: "1rem" }}>
              {nodes.map((n) => (
                <div key={n.id} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "6px 0", borderBottom: "1px solid #f1f5f9" }}>
                  <div>
                    <strong style={{ fontSize: "0.9rem" }}>{n.nodeId}</strong>
                    <span style={{ fontSize: "0.8rem", color: "#64748b", marginLeft: "6px" }}>({n.nodeType})</span>
                  </div>
                  <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
                    <span style={{ fontSize: "0.8rem", color: "#64748b" }}>Batt: {n.batteryLevel ?? "—"}%</span>
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
                  <span style={{ color: "#64748b" }}>RFID UID</span>
                  <strong>{rfidScans[0].uid}</strong>
                </div>
                <div style={{ display: "flex", justifyContent: "space-between" }}>
                  <span style={{ color: "#64748b" }}>Node</span>
                  <strong>{rfidScans[0].node_id}</strong>
                </div>
                <div style={{ display: "flex", justifyContent: "space-between" }}>
                  <span style={{ color: "#64748b" }}>Status</span>
                  <StatusBadge label={rfidScans[0].status} tone={scanTone(rfidScans[0].status)} />
                </div>
                <div style={{ display: "flex", justifyContent: "space-between" }}>
                  <span style={{ color: "#64748b" }}>RSSI</span>
                  <strong>{rfidScans[0].rssi} dBm</strong>
                </div>
                <div style={{ display: "flex", justifyContent: "space-between" }}>
                  <span style={{ color: "#64748b" }}>SNR</span>
                  <strong>{rfidScans[0].snr} dB</strong>
                </div>
                <div style={{ display: "flex", justifyContent: "space-between" }}>
                  <span style={{ color: "#64748b" }}>Time</span>
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
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.85rem" }}>
                <thead>
                  <tr style={{ borderBottom: "1px solid #e2e8f0", textAlign: "left", color: "#64748b" }}>
                    <th style={{ padding: "8px" }}>Time</th>
                    <th style={{ padding: "8px" }}>Node</th>
                    <th style={{ padding: "8px" }}>Checkpoint</th>
                    <th style={{ padding: "8px" }}>Employee</th>
                    <th style={{ padding: "8px" }}>RFID UID</th>
                    <th style={{ padding: "8px" }}>RSSI</th>
                    <th style={{ padding: "8px" }}>SNR</th>
                    <th style={{ padding: "8px" }}>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {rfidScans.map((scan) => (
                    <tr key={scan.id} style={{ borderBottom: "1px solid #f1f5f9" }}>
                      <td style={{ padding: "8px", fontWeight: 500 }}>
                        {new Date(scan.timestamp).toLocaleTimeString()}
                      </td>
                      <td style={{ padding: "8px" }}>{scan.node_id}</td>
                      <td style={{ padding: "8px" }}>{scan.checkpoint_id ?? "—"}</td>
                      <td style={{ padding: "8px" }}>{scan.employee_id ?? "Unknown"}</td>
                      <td style={{ padding: "8px" }}><strong>{scan.uid}</strong></td>
                      <td style={{ padding: "8px" }}>{scan.rssi}</td>
                      <td style={{ padding: "8px" }}>{scan.snr}</td>
                      <td style={{ padding: "8px" }} title={scan.reason ?? undefined}><StatusBadge label={scan.status} tone={scanTone(scan.status)} />{scan.reason && <div style={{ fontSize: "0.72rem", color: "#b91c1c", marginTop: 2 }}>{scan.reason}</div>}</td>
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
