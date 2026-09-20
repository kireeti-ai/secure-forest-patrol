"use client";

import { useEffect, useMemo, useState } from "react";
import { fetchRfidEvents, type RfidEvent } from "../../../lib/rfidApi";
import { StatusBadge } from "../../../components/ui/StatusBadge";

type Filter = "ALL" | "AUTHORIZED" | "INVALID" | "UNKNOWN";
const TABS: { key: Filter; label: string }[] = [
  { key: "ALL", label: "All" },
  { key: "AUTHORIZED", label: "Authorized" },
  { key: "INVALID", label: "Invalid" },
  { key: "UNKNOWN", label: "Unknown" },
];
const TONE = { AUTHORIZED: "healthy", INVALID: "danger", UNKNOWN: "warning" } as const;
const PAGE = 25;

export default function RfidEventsPage() {
  const [events, setEvents] = useState<RfidEvent[]>([]);
  const [error, setError] = useState("");
  const [updated, setUpdated] = useState<Date | null>(null);
  const [filter, setFilter] = useState<Filter>("ALL");
  const [query, setQuery] = useState("");
  const [limit, setLimit] = useState(PAGE);

  useEffect(() => {
    const load = () =>
      fetchRfidEvents()
        .then((rows) => { setEvents(rows); setError(""); setUpdated(new Date()); })
        .catch((e) => setError(e.message));
    load();
    const timer = setInterval(load, 5000);
    return () => clearInterval(timer);
  }, []);

  const counts = useMemo(() => {
    const c: Record<Filter, number> = { ALL: events.length, AUTHORIZED: 0, INVALID: 0, UNKNOWN: 0 };
    for (const e of events) if (e.status in c) c[e.status as Filter]++;
    return c;
  }, [events]);

  const rows = useMemo(() => {
    const q = query.trim().toLowerCase();
    return events.filter((e) =>
      (filter === "ALL" || e.status === filter) &&
      (!q || [e.uid, e.employee_id, e.checkpoint_id, e.node_id].some((v) => v?.toLowerCase().includes(q))));
  }, [events, filter, query]);
  const shown = rows.slice(0, limit);

  return (
    <div className="dashboard-page">
      <div className="scan-head">
        <div>
          <h1>RFID scans</h1>
          <p>Card reads from field nodes, newest first.</p>
        </div>
        <span className={`scan-live${error ? " scan-live-off" : ""}`} role="status">
          {error ? "Connection lost" : updated ? `Live, updated ${updated.toLocaleTimeString([], { hour12: false })}` : "Connecting"}
        </span>
      </div>

      <div className="scan-bar">
        <div className="scan-tabs" role="group" aria-label="Filter by status">
          {TABS.map((t) => (
            <button key={t.key} type="button" className="scan-tab" aria-pressed={filter === t.key}
              onClick={() => { setFilter(t.key); setLimit(PAGE); }}>
              {t.label} <b>{counts[t.key]}</b>
            </button>
          ))}
        </div>
        <input className="scan-search" type="search" placeholder="Search card, officer, checkpoint" value={query}
          onChange={(e) => { setQuery(e.target.value); setLimit(PAGE); }} aria-label="Search scans" />
      </div>

      <div className="scan-wrap">
        <table className="scan-table">
          <thead>
            <tr>
              <th className="c-time">Time</th><th className="c-node">Node</th><th className="c-cp">Checkpoint</th>
              <th className="c-off">Officer</th><th className="c-uid">Card</th><th>Status</th><th className="c-sig num">Signal</th>
            </tr>
          </thead>
          <tbody>
            {shown.map((e) => {
              const t = new Date(e.timestamp);
              return (
                <tr key={e.id} className={e.status === "INVALID" ? "scan-invalid" : undefined}>
                  <td>
                    <span className="t-time">{t.toLocaleTimeString([], { hour12: false })}</span>
                    <span className="t-date">{t.toLocaleDateString([], { day: "2-digit", month: "short", year: "numeric" })}</span>
                  </td>
                  <td>{e.node_id}</td>
                  <td>{e.checkpoint_id ?? "\u2014"}</td>
                  <td>{e.employee_id || <span className="scan-sub">Unregistered</span>}</td>
                  <td className="t-mono">{e.uid}</td>
                  <td>
                    <StatusBadge label={e.status.charAt(0) + e.status.slice(1).toLowerCase()} tone={TONE[e.status as keyof typeof TONE] ?? "neutral"} />
                    {e.reason && <div className="scan-reason">{e.reason}</div>}
                  </td>
                  <td className="num t-mono">
                    {e.rssi ?? "\u2014"} dBm
                    <span className="scan-sub">SNR {e.snr ?? "\u2014"} dB</span>
                  </td>
                </tr>
              );
            })}
            {shown.length === 0 && (
              <tr><td colSpan={7} className="scan-empty">{events.length === 0 ? "No scans yet." : "No scans match this filter."}</td></tr>
            )}
          </tbody>
        </table>
        {rows.length > shown.length && (
          <div className="scan-more"><button type="button" onClick={() => setLimit((n) => n + PAGE)}>Show more ({rows.length - shown.length} left)</button></div>
        )}
      </div>
    </div>
  );
}
