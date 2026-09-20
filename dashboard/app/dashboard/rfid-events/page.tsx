"use client";

import { useEffect, useMemo, useState } from "react";
import { fetchRfidEvents, type RfidEvent } from "../../../lib/rfidApi";
import { Card } from "../../../components/ui/Card";
import { DataTable } from "../../../components/ui/DataTable";
import { SectionHeader } from "../../../components/ui/SectionHeader";
import { StatusBadge } from "../../../components/ui/StatusBadge";

type Filter = "ALL" | "AUTHORIZED" | "INVALID" | "UNKNOWN";
const FILTERS: Filter[] = ["ALL", "AUTHORIZED", "INVALID", "UNKNOWN"];
const TONE = { AUTHORIZED: "healthy", INVALID: "danger", UNKNOWN: "neutral" } as const;

export default function RfidEventsPage() {
  const [events, setEvents] = useState<RfidEvent[]>([]);
  const [error, setError] = useState("");
  const [filter, setFilter] = useState<Filter>("ALL");

  useEffect(() => {
    const load = () => fetchRfidEvents().then((rows) => { setEvents(rows); setError(""); }).catch((e) => setError(e.message));
    load();
    const timer = setInterval(load, 5000);
    return () => clearInterval(timer);
  }, []);

  const counts = useMemo(() => {
    const c: Record<Filter, number> = { ALL: events.length, AUTHORIZED: 0, INVALID: 0, UNKNOWN: 0 };
    for (const e of events) if (e.status in c) c[e.status as Filter]++;
    return c;
  }, [events]);
  const shown = filter === "ALL" ? events : events.filter((e) => e.status === filter);

  return (
    <div className="dashboard-page" style={{ padding: "1.5rem" }}>
      <SectionHeader title="Live RFID Events" description="Card scans from field nodes. Refreshes every 5 seconds." />
      {error && <p role="alert" style={{ color: "#f87171" }}>{error}</p>}

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))", gap: "1rem", margin: "1rem 0 1.5rem" }}>
        {FILTERS.map((f) => (
          <button key={f} onClick={() => setFilter(f)} aria-pressed={filter === f}
            style={{ all: "unset", cursor: "pointer", display: "block" }}>
            <Card style={{ padding: "1rem 1.25rem", outline: filter === f ? "2px solid var(--color-forest-dark, #10b981)" : "none" }}>
              <div style={{ fontSize: "0.7rem", letterSpacing: "0.08em", textTransform: "uppercase", opacity: 0.7 }}>{f === "ALL" ? "All scans" : f}</div>
              <div style={{ fontSize: "1.8rem", fontWeight: 700 }}>{counts[f]}</div>
            </Card>
          </button>
        ))}
      </div>

      <DataTable>
        <table className="data-table">
          <thead>
            <tr><th>Time</th><th>Node</th><th>Checkpoint</th><th>Officer</th><th>Card UID</th><th>Status</th><th>Signal</th></tr>
          </thead>
          <tbody>
            {shown.map((e) => (
              <tr key={e.id}>
                <td style={{ whiteSpace: "nowrap" }}>{new Date(e.timestamp).toLocaleString()}</td>
                <td>{e.node_id}</td>
                <td>{e.checkpoint_id ?? "—"}</td>
                <td>{e.employee_id || "Unknown"}</td>
                <td style={{ fontFamily: "ui-monospace, monospace" }}>{e.uid}</td>
                <td>
                  <StatusBadge label={e.status} tone={TONE[e.status as keyof typeof TONE] ?? "neutral"} />
                  {e.reason && <small>{e.reason}</small>}
                </td>
                <td style={{ whiteSpace: "nowrap" }}>{e.rssi ?? "—"} dBm · {e.snr ?? "—"} dB</td>
              </tr>
            ))}
            {shown.length === 0 && (
              <tr><td colSpan={7} style={{ textAlign: "center", padding: 32 }}>No scans{filter !== "ALL" ? ` with status ${filter}` : " yet"}.</td></tr>
            )}
          </tbody>
        </table>
      </DataTable>
    </div>
  );
}
