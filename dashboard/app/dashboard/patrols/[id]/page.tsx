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
      <span style={{ fontSize: "0.8rem", fontWeight: 600, color: "var(--color-muted)", display: "block", marginBottom: "4px" }}>{label}</span>
      <code style={{ fontSize: "0.78rem", color: "var(--color-text)", wordBreak: "break-all", background: "var(--color-surface-alt)", padding: "6px 10px", borderRadius: "4px", display: "block", border: "1px solid var(--color-border)" }}>
        {value}
      </code>
    </div>
  );
}

function DetailRow({ label, value, tone }: { label: string; value: React.ReactNode; tone?: string }) {
  return (
    <tr>
      <td>{label}</td>
      <td>{value}</td>
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
          <Link href="/dashboard/patrols" style={{ color: "var(--color-muted)", fontSize: "0.85rem", textDecoration: "none" }}>
            ← Back to Patrol Verification Queue
          </Link>
          <h1>
            Patrol Event — {patrol.eventId}
          </h1>
        </div>
      </div>

      {/* IDENTITY VERIFICATION RESULT */}
      <Card style={{ marginBottom: "1.5rem", padding: "1.25rem", background: patrol.recordStatus === "AUTHENTIC" ? "var(--color-healthy-bg)" : "var(--color-danger-bg)" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <div>
            <h2 style={{ fontSize: "1.1rem", fontWeight: 700, color: patrol.recordStatus === "AUTHENTIC" ? "var(--color-healthy)" : "var(--color-danger)" }}>
              {patrol.recordStatus === "AUTHENTIC" ? "Record authentic" : "Record integrity failure"}
            </h2>
            <p style={{ fontSize: "0.85rem", color: "var(--color-text-soft)", marginTop: "4px" }}>
              Signature and hash-chain checks for this record are shown below; the status above reflects the stored verification result.
            </p>
          </div>
          <StatusBadge label={patrol.recordStatus} tone={patrol.recordStatus === "AUTHENTIC" ? "healthy" : "danger"} />
        </div>
      </Card>

      {/* CORE EVENT DATA */}
      <Card style={{ marginBottom: "1.5rem" }}>
        <h3 style={{ padding: "1rem 1rem 0.5rem", fontWeight: 700, color: "var(--color-navy)", borderBottom: "1px solid var(--color-border)" }}>Event Information</h3>
        <table>
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
        <h3 style={{ padding: "1rem 1rem 0.5rem", fontWeight: 700, color: "var(--color-navy)", borderBottom: "1px solid var(--color-border)" }}>Identity Verification</h3>
        <table>
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
                  <span style={{ fontSize: "0.8rem", color: "var(--color-muted)" }}>
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
        <h3 style={{ padding: "1rem 1rem 0.5rem", fontWeight: 700, color: "var(--color-navy)", borderBottom: "1px solid var(--color-border)" }}>
          Tamper-Evident Hash Chain
        </h3>
        <div style={{ padding: "1rem" }}>
          <HashDisplay label="Previous Record Hash (Links to prior event)" value={patrol.previousHash} />
          <HashDisplay label="Current Record Hash (Covers this event data)" value={patrol.currentHash} />
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem", marginTop: "0.5rem" }}>
            <div>
              <span style={{ fontSize: "0.8rem", fontWeight: 600, color: "var(--color-muted)", display: "block", marginBottom: "4px" }}>Signature Status</span>
              <StatusBadge label={patrol.signatureStatus} tone={patrol.signatureStatus === "VALID" ? "healthy" : "danger"} />
            </div>
            <div>
              <span style={{ fontSize: "0.8rem", fontWeight: 600, color: "var(--color-muted)", display: "block", marginBottom: "4px" }}>Ledger Chain Status</span>
              <StatusBadge label={patrol.ledgerStatus} tone={patrol.ledgerStatus === "VALID" ? "healthy" : "danger"} />
            </div>
          </div>
          <div style={{ marginTop: "0.75rem", fontSize: "0.8rem", color: "var(--color-muted)", background: "var(--color-surface-alt)", padding: "8px 12px", borderRadius: "6px", border: "1px solid var(--color-border)" }}>
            <strong>How this works:</strong> Each record is SHA-256 hashed over its payload and chained to the previous hash.
            An RSA private key on the field node signs the hash. A broken chain or invalid signature indicates tampering.
          </div>
        </div>
      </Card>

      {/* SYNCHRONIZATION CHAIN */}
      <Card>
        <h3 style={{ padding: "1rem 1rem 0.5rem", fontWeight: 700, color: "var(--color-navy)", borderBottom: "1px solid var(--color-border)" }}>Offline-First Synchronization Chain</h3>
        <div style={{ padding: "1rem" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "1rem", flexWrap: "wrap", fontSize: "0.85rem" }}>
            <div style={{ textAlign: "center", padding: "10px 16px", background: "var(--color-healthy-bg)", border: "1px solid var(--color-border)", borderRadius: "8px" }}>
              <strong>Field Event Created</strong><br /><span style={{ color: "var(--color-muted)" }}>{patrol.timestamp}</span>
            </div>
            <span style={{ color: "var(--color-faint)", fontSize: "1.2rem" }}>→</span>
            <div style={{ textAlign: "center", padding: "10px 16px", background: "var(--color-surface-alt)", border: "1px solid var(--color-border)", borderRadius: "8px" }}>
              <strong>Gateway Received</strong><br /><span style={{ color: "var(--color-muted)" }}>{patrol.gatewayReceiveTime}</span>
            </div>
            <span style={{ color: "var(--color-faint)", fontSize: "1.2rem" }}>→</span>
            <div style={{ textAlign: "center", padding: "10px 16px", background: "var(--color-surface-alt)", border: "1px solid var(--color-border)", borderRadius: "8px" }}>
              <strong>Backend Received</strong><br /><span style={{ color: "var(--color-muted)" }}>{patrol.backendReceiveTime}</span>
            </div>
            <span style={{ color: "var(--color-faint)", fontSize: "1.2rem" }}>→</span>
            <div>
              <StatusBadge label={patrol.syncStatus} tone={patrol.syncStatus === "SYNCED" ? "healthy" : "warning"} />
            </div>
          </div>
        </div>
      </Card>
    </div>
  );
}
