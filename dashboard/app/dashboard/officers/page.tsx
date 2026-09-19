"use client";

import { useEffect, useState } from "react";
import { fetchOfficerPresence, OfficerPresence } from "../../../lib/rfidApi";
import { Card } from "../../../components/ui/Card";
import { SectionHeader } from "../../../components/ui/SectionHeader";
import { StatusBadge } from "../../../components/ui/StatusBadge";

export default function OfficersPage() {
  const [officers, setOfficers] = useState<OfficerPresence[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  useEffect(() => {
    let active = true;
    const load = () => fetchOfficerPresence().then((data) => { if (active) { setOfficers(data); setError(""); } }).catch((err: Error) => { if (active) setError(err.message); }).finally(() => { if (active) setLoading(false); });
    load(); const timer = setInterval(load, 5000);
    return () => { active = false; clearInterval(timer); };
  }, []);
  const present = officers.filter((officer) => officer.present).length;
  return (
    <div className="dashboard-page" style={{ padding: "1.5rem" }}>
      <header className="page-header" style={{ marginBottom: "1.5rem" }}><h1 style={{ fontSize: "1.75rem", fontWeight: 700, color: "var(--color-navy)" }}>Officer Presence</h1><p style={{ color: "#64748b", marginTop: "4px" }}>Live RFID attendance from the production backend. Green means checked in today; red means absent.</p></header>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(200px, 1fr))", gap: "1rem", marginBottom: "1.5rem" }}>
        <Card style={{ padding: "1.25rem", borderLeft: "4px solid var(--color-navy)" }}><p style={{ fontSize: "0.8rem", fontWeight: 700, color: "#64748b" }}>REGISTERED STAFF</p><p style={{ fontSize: "2rem", fontWeight: 700, color: "var(--color-navy)", marginTop: "4px" }}>{loading ? "..." : officers.length}</p></Card>
        <Card style={{ padding: "1.25rem", borderLeft: "4px solid #16a34a" }}><p style={{ fontSize: "0.8rem", fontWeight: 700, color: "#64748b" }}>PRESENT TODAY</p><p style={{ fontSize: "2rem", fontWeight: 700, color: "#16a34a", marginTop: "4px" }}>{loading ? "..." : present}</p></Card>
        <Card style={{ padding: "1.25rem", borderLeft: "4px solid #dc2626" }}><p style={{ fontSize: "0.8rem", fontWeight: 700, color: "#64748b" }}>ABSENT TODAY</p><p style={{ fontSize: "2rem", fontWeight: 700, color: "#dc2626", marginTop: "4px" }}>{loading ? "..." : officers.length - present}</p></Card>
      </div>
      <Card><SectionHeader title="RFID Officer Registry" /><div style={{ padding: "1rem", overflowX: "auto" }}>
        {error && <p role="alert" style={{ color: "#b91c1c", marginBottom: "1rem" }}>{error}</p>}
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.9rem" }}><thead><tr style={{ borderBottom: "2px solid #e2e8f0", textAlign: "left", color: "#475569" }}><th style={{ padding: "10px" }}>Presence</th><th style={{ padding: "10px" }}>Employee ID</th><th style={{ padding: "10px" }}>Name</th><th style={{ padding: "10px" }}>Role</th><th style={{ padding: "10px" }}>RFID UID</th><th style={{ padding: "10px" }}>Entry</th><th style={{ padding: "10px" }}>Exit</th></tr></thead><tbody>{officers.map((officer) => <tr key={officer.id} style={{ borderBottom: "1px solid #f1f5f9" }}><td style={{ padding: "10px" }}><span style={{ display: "inline-block", width: 10, height: 10, borderRadius: "50%", background: officer.present ? "#16a34a" : "#dc2626" }} /> <span style={{ marginLeft: 6, color: officer.present ? "#16a34a" : "#dc2626", fontWeight: 700 }}>{officer.present ? "PRESENT" : "ABSENT"}</span></td><td style={{ padding: "10px" }}><code>{officer.employee_id ?? "-"}</code></td><td style={{ padding: "10px", fontWeight: 600 }}>{officer.name}</td><td style={{ padding: "10px" }}><StatusBadge label={officer.role} tone="neutral" /></td><td style={{ padding: "10px" }}><code>{officer.rfid_uid ?? "Unassigned"}</code></td><td style={{ padding: "10px", color: "#64748b" }}>{officer.entry_at ? new Date(officer.entry_at).toLocaleTimeString() : "-"}</td><td style={{ padding: "10px", color: "#64748b" }}>{officer.exit_at ? new Date(officer.exit_at).toLocaleTimeString() : "-"}</td></tr>)}</tbody></table>
        {!loading && officers.length === 0 && !error && <p style={{ padding: "1rem", color: "#64748b" }}>No real RFID staff records are registered yet.</p>}
      </div></Card>
    </div>
  );
}
