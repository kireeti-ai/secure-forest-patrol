"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { fetchPatrols, PatrolRecord } from "../../../lib/api";
import { Card } from "../../../components/ui/Card";
import { SectionHeader } from "../../../components/ui/SectionHeader";
import { StatusBadge } from "../../../components/ui/StatusBadge";
import { useForestWebSocket } from "../../../lib/ws";

export default function PatrolsPage() {
  const [patrols, setPatrols] = useState<PatrolRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const loadRef = useRef<() => void>(() => {});

  useEffect(() => {
    async function load() {
      const data = await fetchPatrols();
      setPatrols(data);
      setLoading(false);
    }
    loadRef.current = load;
    load();
  }, []);

  useForestWebSocket(
    ["PATROL_EVENT_VERIFIED", "PATROL_EVENT_REJECTED", "LEDGER_VERIFICATION_RESULT"],
    () => loadRef.current(),
    () => loadRef.current()
  );

  return (
    <div className="dashboard-page" style={{ padding: "1.5rem" }}>
      <header className="page-header" style={{ marginBottom: "1.5rem" }}>
        <h1 style={{ fontSize: "1.75rem", fontWeight: 700, color: "var(--color-navy)" }}>Patrol Verification Queue</h1>
        <p style={{ color: "#64748b", marginTop: "4px" }}>
          Authenticity verification of field officer check-ins, RFID tags, fingerprint matches, RSA signatures, and ledger hash integrity.
        </p>
      </header>

      <Card>
        <SectionHeader title="Patrol Records" />
        <div style={{ padding: "1rem", overflowX: "auto" }}>
          {loading ? (
            <p>Loading patrol records...</p>
          ) : (
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.88rem" }}>
              <thead>
                <tr style={{ borderBottom: "2px solid #e2e8f0", textAlign: "left", color: "#475569" }}>
                  <th style={{ padding: "10px" }}>Event ID</th>
                  <th style={{ padding: "10px" }}>Timestamp</th>
                  <th style={{ padding: "10px" }}>Checkpoint</th>
                  <th style={{ padding: "10px" }}>Officer</th>
                  <th style={{ padding: "10px" }}>RFID Status</th>
                  <th style={{ padding: "10px" }}>Biometric Match</th>
                  <th style={{ padding: "10px" }}>Signature</th>
                  <th style={{ padding: "10px" }}>Ledger Chain</th>
                  <th style={{ padding: "10px" }}>Sync Status</th>
                  <th style={{ padding: "10px" }}>Action</th>
                </tr>
              </thead>
              <tbody>
                {patrols.map((p) => (
                  <tr key={p.id} style={{ borderBottom: "1px solid #f1f5f9" }}>
                    <td style={{ padding: "10px", fontWeight: 700, color: "var(--color-navy)" }}>{p.eventId}</td>
                    <td style={{ padding: "10px" }}>{p.timestamp}</td>
                    <td style={{ padding: "10px" }}>
                      <strong>{p.checkpointId}</strong> <span style={{ color: "#64748b" }}>({p.nodeId})</span>
                    </td>
                    <td style={{ padding: "10px" }}>
                      {p.officerName} <span style={{ color: "#64748b", fontSize: "0.8rem" }}>({p.officerId})</span>
                    </td>
                    <td style={{ padding: "10px" }}>
                      <StatusBadge label={p.rfidStatus} tone={p.rfidStatus === "VALID" ? "healthy" : "danger"} />
                    </td>
                    <td style={{ padding: "10px" }}>
                      <StatusBadge label={p.fingerprintStatus} tone={p.fingerprintStatus === "MATCH" ? "healthy" : "danger"} />
                    </td>
                    <td style={{ padding: "10px" }}>
                      <StatusBadge label={p.signatureStatus} tone={p.signatureStatus === "VALID" ? "healthy" : "danger"} />
                    </td>
                    <td style={{ padding: "10px" }}>
                      <StatusBadge label={p.ledgerStatus} tone={p.ledgerStatus === "VALID" ? "healthy" : "danger"} />
                    </td>
                    <td style={{ padding: "10px" }}>
                      <StatusBadge label={p.syncStatus} tone={p.syncStatus === "SYNCED" ? "healthy" : "warning"} />
                    </td>
                    <td style={{ padding: "10px" }}>
                      <Link
                        href={`/dashboard/patrols/${p.id}`}
                        style={{
                          padding: "4px 10px",
                          fontSize: "0.8rem",
                          fontWeight: 600,
                          color: "#0369a1",
                          border: "1px solid #bae6fd",
                          borderRadius: "4px",
                          background: "#f0f9ff",
                          textDecoration: "none",
                        }}
                      >
                        Inspect →
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </Card>
    </div>
  );
}
