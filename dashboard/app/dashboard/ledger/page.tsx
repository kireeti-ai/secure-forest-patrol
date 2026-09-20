"use client";

import { useEffect, useState } from "react";
import { fetchLedger, LedgerRecord } from "../../../lib/api";
import { Card } from "../../../components/ui/Card";
import { SectionHeader } from "../../../components/ui/SectionHeader";
import { StatusBadge } from "../../../components/ui/StatusBadge";

function truncateHash(hash: string, len = 16) {
  if (!hash) return "—";
  return hash.length > len ? `${hash.slice(0, len)}…` : hash;
}

export default function LedgerPage() {
  const [records, setRecords] = useState<LedgerRecord[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      const data = await fetchLedger();
      setRecords(data);
      setLoading(false);
    }
    load();
  }, []);

  const validCount = records.filter((r) => r.chainStatus === "VALID").length;
  const brokenCount = records.filter((r) => r.chainStatus !== "VALID" && r.chainStatus !== "PENDING").length;

  return (
    <div className="dashboard-page">
      <header className="page-header">
        <h1>Ledger</h1>
        <p>Hash-chained patrol records and their verification status.</p>
      </header>

      <div className="stat-grid">
        <Card className="stat">
          <p className="stat-label">Valid chain records</p>
          <p className="stat-value" style={{ color: "var(--color-healthy)" }}>{loading ? "..." : validCount}</p>
        </Card>
        <Card className="stat">
          <p className="stat-label">Chain failures</p>
          <p className="stat-value" style={{ color: brokenCount > 0 ? "var(--color-danger)" : "var(--color-healthy)" }}>{loading ? "..." : brokenCount}</p>
        </Card>
        <Card className="stat">
          <p className="stat-label">Total records</p>
          <p className="stat-value" style={{ color: "var(--color-navy)" }}>{loading ? "..." : records.length}</p>
        </Card>
      </div>

      <Card>
        <SectionHeader title="Hash Chain Records" />
        <div style={{ padding: "1rem", overflowX: "auto" }}>
          <table>
            <thead>
              <tr>
                <th>Seq #</th>
                <th>Node ID</th>
                <th>Timestamp</th>
                <th>Previous Hash</th>
                <th>Current Hash</th>
                <th>Signature</th>
                <th>Chain Status</th>
                <th>Duplicate</th>
              </tr>
            </thead>
            <tbody>
              {records.map((r) => (
                <tr
                  key={r.sequence}
                  style={{
                    borderBottom: "1px solid var(--color-surface-alt)",
                    background: r.chainStatus !== "VALID" && r.chainStatus !== "PENDING" ? "var(--color-danger-bg)" : "transparent",
                  }}
                >
                  <td>#{r.sequence}</td>
                  <td>{r.nodeId}</td>
                  <td>{r.timestamp}</td>
                  <td title={r.previousHash}>
                    <code style={{ fontSize: "0.8rem", color: "var(--color-text-soft)" }}>{truncateHash(r.previousHash)}</code>
                  </td>
                  <td title={r.currentHash}>
                    <code style={{ fontSize: "0.8rem", color: "var(--color-text-soft)" }}>{truncateHash(r.currentHash)}</code>
                  </td>
                  <td>
                    <StatusBadge label={r.signatureStatus} tone={r.signatureStatus === "VALID" ? "healthy" : "danger"} />
                  </td>
                  <td>
                    <StatusBadge label={r.chainStatus} tone={r.chainStatus === "VALID" ? "healthy" : "danger"} />
                  </td>
                  <td>
                    <StatusBadge label={r.duplicateStatus} tone={r.duplicateStatus === "UNIQUE" ? "healthy" : "warning"} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      <div style={{ marginTop: "1rem", padding: "12px 16px", background: "var(--color-surface-alt)", border: "1px solid var(--color-border)", borderRadius: "8px", fontSize: "0.82rem", color: "var(--color-muted)" }}>
        <strong>How to read this table:</strong> Each record&apos;s <em>Previous Hash</em> must equal the <em>Current Hash</em> of the record with Seq# − 1.
        A broken chain signals data tampering or a missing record. A bad signature means the record was not produced by the legitimate node key.
        Hover any truncated hash to see the full value.
      </div>
    </div>
  );
}
