"use client";

import { useEffect, useState } from "react";
import { fetchOfficers, Officer } from "../../../lib/api";
import { Card } from "../../../components/ui/Card";
import { SectionHeader } from "../../../components/ui/SectionHeader";
import { StatusBadge } from "../../../components/ui/StatusBadge";

export default function OfficersPage() {
  const [officers, setOfficers] = useState<Officer[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      const data = await fetchOfficers();
      setOfficers(data);
      setLoading(false);
    }
    load();
  }, []);

  const totalMismatches = officers.reduce((acc, o) => acc + o.mismatchCount, 0);

  return (
    <div className="dashboard-page" style={{ padding: "1.5rem" }}>
      <header className="page-header" style={{ marginBottom: "1.5rem" }}>
        <h1 style={{ fontSize: "1.75rem", fontWeight: 700, color: "var(--color-navy)" }}>Forest Patrol Officers</h1>
        <p style={{ color: "#64748b", marginTop: "4px" }}>
          Registered patrol officers, their verification history, assigned checkpoints, and identity mismatch statistics.
        </p>
      </header>

      {/* SUMMARY STRIP */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(200px, 1fr))", gap: "1rem", marginBottom: "1.5rem" }}>
        <Card style={{ padding: "1.25rem", borderLeft: "4px solid var(--color-navy)" }}>
          <p style={{ fontSize: "0.8rem", fontWeight: 700, color: "#64748b" }}>TOTAL OFFICERS</p>
          <p style={{ fontSize: "2rem", fontWeight: 700, color: "var(--color-navy)", marginTop: "4px" }}>{loading ? "..." : officers.length}</p>
        </Card>
        <Card style={{ padding: "1.25rem", borderLeft: "4px solid #16a34a" }}>
          <p style={{ fontSize: "0.8rem", fontWeight: 700, color: "#64748b" }}>ACTIVE</p>
          <p style={{ fontSize: "2rem", fontWeight: 700, color: "#16a34a", marginTop: "4px" }}>
            {loading ? "..." : officers.filter((o) => o.state === "ACTIVE").length}
          </p>
        </Card>
        <Card style={{ padding: "1.25rem", borderLeft: "4px solid #dc2626" }}>
          <p style={{ fontSize: "0.8rem", fontWeight: 700, color: "#64748b" }}>IDENTITY MISMATCHES</p>
          <p style={{ fontSize: "2rem", fontWeight: 700, color: totalMismatches > 0 ? "#dc2626" : "#16a34a", marginTop: "4px" }}>
            {loading ? "..." : totalMismatches}
          </p>
        </Card>
      </div>

      <Card>
        <SectionHeader title="Officer Registry" />
        <div style={{ padding: "1rem", overflowX: "auto" }}>
          {loading ? (
            <p>Loading officer data...</p>
          ) : (
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.9rem" }}>
              <thead>
                <tr style={{ borderBottom: "2px solid #e2e8f0", textAlign: "left", color: "#475569" }}>
                  <th style={{ padding: "10px" }}>Badge #</th>
                  <th style={{ padding: "10px" }}>Officer ID</th>
                  <th style={{ padding: "10px" }}>Name</th>
                  <th style={{ padding: "10px" }}>State</th>
                  <th style={{ padding: "10px" }}>Assigned Checkpoint</th>
                  <th style={{ padding: "10px" }}>Total Patrols</th>
                  <th style={{ padding: "10px" }}>Identity Mismatches</th>
                  <th style={{ padding: "10px" }}>Last Verified Patrol</th>
                </tr>
              </thead>
              <tbody>
                {officers.map((o) => (
                  <tr key={o.id} style={{ borderBottom: "1px solid #f1f5f9" }}>
                    <td style={{ padding: "10px", fontWeight: 700, color: "var(--color-navy)" }}>{o.badgeNumber}</td>
                    <td style={{ padding: "10px" }}><code style={{ fontSize: "0.85rem" }}>{o.officerId}</code></td>
                    <td style={{ padding: "10px", fontWeight: 600 }}>{o.name}</td>
                    <td style={{ padding: "10px" }}>
                      <StatusBadge label={o.state} tone={o.state === "ACTIVE" ? "healthy" : "warning"} />
                    </td>
                    <td style={{ padding: "10px" }}>{o.assignedCheckpoint ?? "—"}</td>
                    <td style={{ padding: "10px" }}>{o.patrolCount}</td>
                    <td style={{ padding: "10px" }}>
                      {o.mismatchCount > 0 ? (
                        <span style={{ color: "#dc2626", fontWeight: 700 }}>{o.mismatchCount} ⚠</span>
                      ) : (
                        <span style={{ color: "#16a34a", fontWeight: 600 }}>0</span>
                      )}
                    </td>
                    <td style={{ padding: "10px", color: "#64748b" }}>{o.lastVerifiedPatrol ?? "—"}</td>
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
