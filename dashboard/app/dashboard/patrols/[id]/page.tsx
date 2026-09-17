"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { fetchPatrolById, PatrolRecord } from "../../../../lib/api";
import { Card } from "../../../../components/ui/Card";
import { StatusBadge } from "../../../../components/ui/StatusBadge";

function HashDisplay({ label, value }: { label: string; value: string }) {
  return (
    <div style={{ marginBottom: "0.75rem" }}>
      <span style={{ fontSize: "0.8rem", fontWeight: 600, color: "#64748b", display: "block", marginBottom: "4px" }}>{label}</span>
      <code style={{ fontSize: "0.78rem", color: "#334155", wordBreak: "break-all", background: "#f8fafc", padding: "6px 10px", borderRadius: "4px", display: "block", border: "1px solid #e2e8f0" }}>
        {value}
      </code>
    </div>
  );
}

function DetailRow({ label, value, tone }: { label: string; value: React.ReactNode; tone?: string }) {
  return (
    <tr style={{ borderBottom: "1px solid #f1f5f9" }}>
      <td style={{ padding: "10px 16px", color: "#64748b", fontWeight: 600, width: "200px", whiteSpace: "nowrap" }}>{label}</td>
      <td style={{ padding: "10px 16px", color: "#0f172a" }}>{value}</td>
    </tr>
  );
}

export default function PatrolDetailPage() {
  const params = useParams();
  const [patrol, setPatrol] = useState<PatrolRecord | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      const id = typeof params.id === "string" ? params.id : params.id?.[0] || "";
      const data = await fetchPatrolById(id);
      setPatrol(data);
      setLoading(false);
    }
    load();
  }, [params.id]);

  if (loading) return <div style={{ padding: "2rem" }}>Loading patrol event detail...</div>;
  if (!patrol) return <div style={{ padding: "2rem" }}>Patrol event not found.</div>;

  return (
    <div className="dashboard-page" style={{ padding: "1.5rem", maxWidth: "900px" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1.5rem" }}>
        <div>
          <Link href="/dashboard/patrols" style={{ color: "#64748b", fontSize: "0.85rem", textDecoration: "none" }}>
            ← Back to Patrol Verification Queue
          </Link>
          <h1 style={{ fontSize: "1.75rem", fontWeight: 700, color: "var(--color-navy)", marginTop: "6px" }}>
            Patrol Event — {patrol.eventId}
          </h1>
        </div>
        {patrol.isDemo && (
          <span style={{ padding: "6px 14px", borderRadius: "20px", background: "#fef3c7", color: "#92400e", border: "1px solid #fde68a", fontWeight: 700, fontSize: "0.8rem" }}>
            DEMO / MOCK / NOT CONNECTED
          </span>
        )}
      </div>

      {/* IDENTITY VERIFICATION RESULT */}
      <Card style={{ marginBottom: "1.5rem", padding: "1.25rem", background: patrol.recordStatus === "AUTHENTIC" ? "#f0fdf4" : "#fef2f2", borderLeft: "4px solid " + (patrol.recordStatus === "AUTHENTIC" ? "#16a34a" : "#dc2626") }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <div>
            <h2 style={{ fontSize: "1.1rem", fontWeight: 700, color: patrol.recordStatus === "AUTHENTIC" ? "#15803d" : "#991b1b" }}>
              {patrol.recordStatus === "AUTHENTIC" ? "✓ Record Authentic" : "✗ Record Integrity Failure"}
            </h2>
            <p style={{ fontSize: "0.85rem", color: "#475569", marginTop: "4px" }}>
              RFID identity confirmed and fingerprint biometric verified at checkpoint. RSA signature validates record origin.
              Hash chain confirms tamper-evident integrity.
            </p>
          </div>
          <StatusBadge label={patrol.recordStatus} tone={patrol.recordStatus === "AUTHENTIC" ? "healthy" : "danger"} />
        </div>
      </Card>

      {/* CORE EVENT DATA */}
      <Card style={{ marginBottom: "1.5rem" }}>
        <h3 style={{ padding: "1rem 1rem 0.5rem", fontWeight: 700, color: "var(--color-navy)", borderBottom: "1px solid #e2e8f0" }}>Event Information</h3>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.9rem" }}>
          <tbody>
            <DetailRow label="Event ID" value={<strong>{patrol.eventId}</strong>} />
            <DetailRow label="Node ID" value={<code>{patrol.nodeId}</code>} />
            <DetailRow label="Checkpoint ID" value={patrol.checkpointId} />
            <DetailRow label="Officer ID" value={patrol.officerId} />
            <DetailRow label="Event Timestamp" value={<strong>{patrol.timestamp}</strong>} />
            <DetailRow label="Gateway Received" value={patrol.gatewayReceiveTime} />
            <DetailRow label="Backend Received" value={patrol.backendReceiveTime} />
            <DetailRow label="Sequence #" value={patrol.sequence} />
          </tbody>
        </table>
      </Card>

      {/* IDENTITY VERIFICATION PANEL */}
      <Card style={{ marginBottom: "1.5rem" }}>
        <h3 style={{ padding: "1rem 1rem 0.5rem", fontWeight: 700, color: "var(--color-navy)", borderBottom: "1px solid #e2e8f0" }}>Identity Verification</h3>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.9rem" }}>
          <tbody>
            <DetailRow label="RFID Tag" value={patrol.rfid} />
            <DetailRow
              label="RFID Status"
              value={<StatusBadge label={patrol.rfidStatus} tone={patrol.rfidStatus === "VALID" ? "healthy" : "danger"} />}
            />
            <DetailRow
              label="Fingerprint Verification"
              value={
                <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
                  <StatusBadge label={patrol.fingerprintStatus} tone={patrol.fingerprintStatus === "MATCH" ? "healthy" : "danger"} />
                  <span style={{ fontSize: "0.8rem", color: "#64748b" }}>
                    Note: Only the verification result is displayed. Raw biometric templates are not transmitted or stored.
                  </span>
                </div>
              }
            />
          </tbody>
        </table>
      </Card>

      {/* TAMPER-EVIDENT CHAIN */}
      <Card style={{ marginBottom: "1.5rem" }}>
        <h3 style={{ padding: "1rem 1rem 0.5rem", fontWeight: 700, color: "var(--color-navy)", borderBottom: "1px solid #e2e8f0" }}>
          Tamper-Evident Hash Chain
        </h3>
        <div style={{ padding: "1rem" }}>
          <HashDisplay label="Previous Record Hash (Links to prior event)" value={patrol.previousHash} />
          <HashDisplay label="Current Record Hash (Covers this event data)" value={patrol.currentHash} />
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem", marginTop: "0.5rem" }}>
            <div>
              <span style={{ fontSize: "0.8rem", fontWeight: 600, color: "#64748b", display: "block", marginBottom: "4px" }}>Signature Status</span>
              <StatusBadge label={patrol.signatureStatus} tone={patrol.signatureStatus === "VALID" ? "healthy" : "danger"} />
            </div>
            <div>
              <span style={{ fontSize: "0.8rem", fontWeight: 600, color: "#64748b", display: "block", marginBottom: "4px" }}>Ledger Chain Status</span>
              <StatusBadge label={patrol.ledgerStatus} tone={patrol.ledgerStatus === "VALID" ? "healthy" : "danger"} />
            </div>
          </div>
          <div style={{ marginTop: "0.75rem", fontSize: "0.8rem", color: "#64748b", background: "#f8fafc", padding: "8px 12px", borderRadius: "6px", border: "1px solid #e2e8f0" }}>
            <strong>How this works:</strong> Each record is SHA-256 hashed over its payload and chained to the previous hash.
            An RSA private key on the field node signs the hash. A broken chain or invalid signature indicates tampering.
          </div>
        </div>
      </Card>

      {/* SYNCHRONIZATION CHAIN */}
      <Card>
        <h3 style={{ padding: "1rem 1rem 0.5rem", fontWeight: 700, color: "var(--color-navy)", borderBottom: "1px solid #e2e8f0" }}>Offline-First Synchronization Chain</h3>
        <div style={{ padding: "1rem" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "1rem", flexWrap: "wrap", fontSize: "0.85rem" }}>
            <div style={{ textAlign: "center", padding: "10px 16px", background: "#f0fdf4", border: "1px solid #bbf7d0", borderRadius: "8px" }}>
              <strong>Field Event Created</strong><br /><span style={{ color: "#64748b" }}>{patrol.timestamp}</span>
            </div>
            <span style={{ color: "#94a3b8", fontSize: "1.2rem" }}>→</span>
            <div style={{ textAlign: "center", padding: "10px 16px", background: "#f0f9ff", border: "1px solid #bae6fd", borderRadius: "8px" }}>
              <strong>Gateway Received</strong><br /><span style={{ color: "#64748b" }}>{patrol.gatewayReceiveTime}</span>
            </div>
            <span style={{ color: "#94a3b8", fontSize: "1.2rem" }}>→</span>
            <div style={{ textAlign: "center", padding: "10px 16px", background: "#faf5ff", border: "1px solid #e9d5ff", borderRadius: "8px" }}>
              <strong>Backend Received</strong><br /><span style={{ color: "#64748b" }}>{patrol.backendReceiveTime}</span>
            </div>
            <span style={{ color: "#94a3b8", fontSize: "1.2rem" }}>→</span>
            <div>
              <StatusBadge label={patrol.syncStatus} tone={patrol.syncStatus === "SYNCED" ? "healthy" : "warning"} />
            </div>
          </div>
        </div>
      </Card>
    </div>
  );
}
