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
    <div className="dashboard-page" style={{ padding: "1.5rem" }}>
      <header className="page-header" style={{ marginBottom: "1.5rem" }}>
        <h1 style={{ fontSize: "1.75rem", fontWeight: 700, color: "var(--color-navy)" }}>Tamper-Evident Ledger Integrity</h1>
        <p style={{ color: "#64748b", marginTop: "4px" }}>
          Local hash chain inspector. Each record contains a SHA-256 hash chained to the previous record and signed with the node&apos;s RSA private key.
        </p>
      </header>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(200px, 1fr))", gap: "1rem", marginBottom: "1.5rem" }}>
        <Card style={{ padding: "1.25rem", borderLeft: "4px solid #16a34a" }}>
          <p style={{ fontSize: "0.8rem", fontWeight: 700, color: "#64748b" }}>VALID CHAIN RECORDS</p>
          <p style={{ fontSize: "2rem", fontWeight: 700, color: "#16a34a" }}>{loading ? "..." : validCount}</p>
        </Card>
        <Card style={{ padding: "1.25rem", borderLeft: "4px solid #dc2626" }}>
          <p style={{ fontSize: "0.8rem", fontWeight: 700, color: "#64748b" }}>CHAIN FAILURES</p>
          <p style={{ fontSize: "2rem", fontWeight: 700, color: brokenCount > 0 ? "#dc2626" : "#16a34a" }}>{loading ? "..." : brokenCount}</p>
        </Card>
        <Card style={{ padding: "1.25rem", borderLeft: "4px solid var(--color-navy)" }}>
          <p style={{ fontSize: "0.8rem", fontWeight: 700, color: "#64748b" }}>TOTAL RECORDS</p>
          <p style={{ fontSize: "2rem", fontWeight: 700, color: "var(--color-navy)" }}>{loading ? "..." : records.length}</p>
        </Card>
      </div>

      <Card>
        <SectionHeader title="Hash Chain Records" />
        <div style={{ padding: "1rem", overflowX: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.88rem", fontFamily: "monospace" }}>
            <thead>
              <tr style={{ borderBottom: "2px solid #e2e8f0", textAlign: "left", color: "#475569", fontFamily: "inherit" }}>
                <th style={{ padding: "10px" }}>Seq #</th>
                <th style={{ padding: "10px" }}>Node ID</th>
                <th style={{ padding: "10px" }}>Timestamp</th>
                <th style={{ padding: "10px" }}>Previous Hash</th>
                <th style={{ padding: "10px" }}>Current Hash</th>
                <th style={{ padding: "10px" }}>Signature</th>
                <th style={{ padding: "10px" }}>Chain Status</th>
                <th style={{ padding: "10px" }}>Duplicate</th>
              </tr>
            </thead>
            <tbody>
              {records.map((r) => (
                <tr
                  key={r.sequence}
                  style={{
                    borderBottom: "1px solid #f1f5f9",
                    background: r.chainStatus !== "VALID" && r.chainStatus !== "PENDING" ? "#fef2f2" : "transparent",
                  }}
                >
                  <td style={{ padding: "10px", fontWeight: 700, color: "var(--color-navy)" }}>#{r.sequence}</td>
                  <td style={{ padding: "10px" }}>{r.nodeId}</td>
                  <td style={{ padding: "10px", fontFamily: "sans-serif", fontSize: "0.8rem" }}>{r.timestamp}</td>
                  <td style={{ padding: "10px" }} title={r.previousHash}>
                    <code style={{ fontSize: "0.8rem", color: "#475569" }}>{truncateHash(r.previousHash)}</code>
                  </td>
                  <td style={{ padding: "10px" }} title={r.currentHash}>
                    <code style={{ fontSize: "0.8rem", color: "#475569" }}>{truncateHash(r.currentHash)}</code>
                  </td>
                  <td style={{ padding: "10px" }}>
                    <StatusBadge label={r.signatureStatus} tone={r.signatureStatus === "VALID" ? "healthy" : "danger"} />
                  </td>
                  <td style={{ padding: "10px" }}>
                    <StatusBadge label={r.chainStatus} tone={r.chainStatus === "VALID" ? "healthy" : "danger"} />
                  </td>
                  <td style={{ padding: "10px" }}>
                    <StatusBadge label={r.duplicateStatus} tone={r.duplicateStatus === "UNIQUE" ? "healthy" : "warning"} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      <div style={{ marginTop: "1rem", padding: "12px 16px", background: "#f8fafc", border: "1px solid #e2e8f0", borderRadius: "8px", fontSize: "0.82rem", color: "#64748b" }}>
        <strong>How to read this table:</strong> Each record&apos;s <em>Previous Hash</em> must equal the <em>Current Hash</em> of the record with Seq# − 1.
        A broken chain signals data tampering or a missing record. A bad signature means the record was not produced by the legitimate node key.
        Hover any truncated hash to see the full value.
      </div>
    </div>
  );
}
