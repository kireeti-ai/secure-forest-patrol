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
    <div className="dashboard-page">
      <header className="page-header">
        <h1>Patrols</h1>
        <p>Patrol records and their signature and hash-chain checks.</p>
      </header>

      <Card>
        <SectionHeader title="Patrol Records" />
        <div style={{ padding: "1rem", overflowX: "auto" }}>
          {loading ? (
            <p>Loading patrol records...</p>
          ) : (
            <table>
              <thead>
                <tr>
                  <th>Event ID</th>
                  <th>Timestamp</th>
                  <th>Checkpoint</th>
                  <th>Officer</th>
                  <th>RFID Status</th>
                  <th>Biometric Match</th>
                  <th>Signature</th>
                  <th>Ledger Chain</th>
                  <th>Sync Status</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {patrols.map((p) => (
                  <tr key={p.id}>
                    <td>{p.eventId}</td>
                    <td>{p.timestamp}</td>
                    <td>
                      <strong>{p.checkpointId}</strong> <span style={{ color: "var(--color-muted)" }}>({p.nodeId})</span>
                    </td>
                    <td>
                      {p.officerName} <span style={{ color: "var(--color-muted)", fontSize: "0.8rem" }}>({p.officerId})</span>
                    </td>
                    <td>
                      <StatusBadge label={p.rfidStatus} tone={p.rfidStatus === "VALID" ? "healthy" : "danger"} />
                    </td>
                    <td>
                      <StatusBadge label={p.fingerprintStatus} tone={p.fingerprintStatus === "MATCH" ? "healthy" : "danger"} />
                    </td>
                    <td>
                      <StatusBadge label={p.signatureStatus} tone={p.signatureStatus === "VALID" ? "healthy" : "danger"} />
                    </td>
                    <td>
                      <StatusBadge label={p.ledgerStatus} tone={p.ledgerStatus === "VALID" ? "healthy" : "danger"} />
                    </td>
                    <td>
                      <StatusBadge label={p.syncStatus} tone={p.syncStatus === "SYNCED" ? "healthy" : "warning"} />
                    </td>
                    <td>
                      <Link
                        href={`/dashboard/patrols/${p.id}`}
                        style={{
                          padding: "4px 10px",
                          fontSize: "0.8rem",
                          fontWeight: 600,
                          color: "var(--color-forest-dark)",
                          border: "1px solid var(--color-border)",
                          borderRadius: "4px",
                          background: "var(--color-surface-alt)",
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
