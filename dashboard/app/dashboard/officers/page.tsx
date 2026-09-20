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
    <div className="dashboard-page">
      <header className="page-header" style={{ marginBottom: "1.5rem" }}><h1>Officers</h1><p style={{ color: "var(--color-muted)", marginTop: "4px" }}>Attendance from RFID card scans today.</p></header>
      <div className="stat-grid">
        <Card className="stat"><p className="stat-label">Registered</p><p className="stat-value" style={{ color: "var(--color-navy)" }}>{loading ? "..." : officers.length}</p></Card>
        <Card className="stat"><p className="stat-label">Present today</p><p className="stat-value" style={{ color: "var(--color-healthy)" }}>{loading ? "..." : present}</p></Card>
        <Card className="stat"><p className="stat-label">Absent today</p><p className="stat-value" style={{ color: "var(--color-danger)" }}>{loading ? "..." : officers.length - present}</p></Card>
      </div>
      <Card><SectionHeader title="Officer registry" /><div style={{ padding: "1rem", overflowX: "auto" }}>
        {error && <p role="alert" style={{ color: "var(--color-danger)", marginBottom: "1rem" }}>{error}</p>}
        <table><thead><tr><th>Presence</th><th>Employee ID</th><th>Name</th><th>Role</th><th>Checkpoints</th><th>RFID UID</th><th>Entry</th><th>Exit</th></tr></thead><tbody>{officers.map((officer) => <tr key={officer.id}><td><span style={{ display: "inline-block", width: 10, height: 10, borderRadius: "50%", background: officer.present ? "var(--color-healthy)" : "var(--color-danger)" }} /> <span style={{ marginLeft: 6, color: officer.present ? "var(--color-healthy)" : "var(--color-danger)", fontWeight: 700 }}>{officer.present ? "PRESENT" : "ABSENT"}</span></td><td><code>{officer.employee_id ?? "-"}</code></td><td>{officer.name}</td><td><StatusBadge label={officer.role} tone="neutral" /></td><td>{officer.checkpoints.length ? officer.checkpoints.join(", ") : "-"}</td><td><code>{officer.rfid_uid ?? "Unassigned"}</code></td><td>{officer.entry_at ? new Date(officer.entry_at).toLocaleTimeString() : "-"}</td><td>{officer.exit_at ? new Date(officer.exit_at).toLocaleTimeString() : "-"}</td></tr>)}</tbody></table>
        {!loading && officers.length === 0 && !error && <p style={{ padding: "1rem", color: "var(--color-muted)" }}>No real RFID staff records are registered yet.</p>}
      </div></Card>
    </div>
  );
}
