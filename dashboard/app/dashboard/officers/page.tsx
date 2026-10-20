"use client";

import { useEffect, useMemo, useState } from "react";
import { fetchOfficerPresence, fetchVerificationEvents, OfficerPresence, PresenceState, VerificationEvent } from "../../../lib/rfidApi";
import { Card } from "../../../components/ui/Card";
import { SectionHeader } from "../../../components/ui/SectionHeader";
import { StatusBadge } from "../../../components/ui/StatusBadge";

const STATES: { key: PresenceState; label: string; tone: "healthy" | "neutral" | "warning" | "danger"; help: string }[] = [
  { key: "PRESENT", label: "Present", tone: "healthy", help: "scanned in today and not out yet" },
  { key: "CHECKED_OUT", label: "Checked out", tone: "neutral", help: "scanned in and out today" },
  { key: "YET_TO_ARRIVE", label: "Yet to arrive", tone: "warning", help: "no scan yet, still before the cut-off" },
  { key: "ABSENT", label: "Absent", tone: "danger", help: "no scan today and the cut-off has passed" },
];

// Older backends only send `present`; treat a missing state conservatively.
function stateOf(o: OfficerPresence): PresenceState {
  if (o.state) return o.state;
  if (o.present) return "PRESENT";
  return o.entry_at ? "CHECKED_OUT" : "YET_TO_ARRIVE";
}

const clock = (iso: string | null) => (iso ? new Date(iso).toLocaleTimeString([], { hour12: false, hour: "2-digit", minute: "2-digit" }) : "—");

export default function OfficersPage() {
  const [officers, setOfficers] = useState<OfficerPresence[]>([]);
  const [proxyAttempts, setProxyAttempts] = useState<VerificationEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    const load = () =>
      fetchOfficerPresence()
        .then((data) => { if (active) { setOfficers(data); setError(""); } })
        .catch((err: Error) => { if (active) setError(err.message); })
        .finally(() => { if (active) setLoading(false); });
    load();
    const timer = setInterval(load, 5000);
    return () => { active = false; clearInterval(timer); };
  }, []);

  useEffect(() => {
    let active = true;
    const load = () => fetchVerificationEvents("MISMATCH").then((data) => { if (active) setProxyAttempts(data); }).catch(() => {});
    load();
    const timer = setInterval(load, 5000);
    return () => { active = false; clearInterval(timer); };
  }, []);

  const counts = useMemo(() => {
    const c: Record<PresenceState, number> = { PRESENT: 0, CHECKED_OUT: 0, YET_TO_ARRIVE: 0, ABSENT: 0 };
    for (const o of officers) c[stateOf(o)]++;
    return c;
  }, [officers]);

  const cutoff = officers[0]?.absent_after ?? "10:00";
  const tz = officers[0]?.timezone ?? "";
  const shown = (v: number) => (loading ? "…" : v);

  return (
    <div className="dashboard-page">
      <header className="page-header">
        <h1>Officers</h1>
        <p>Who has scanned in today. Checkpoints are two-factor: a card tap, then a matching fingerprint within the window.</p>
      </header>

      <div className="stat-grid">
        <Card className="stat"><p className="stat-label">Registered</p><p className="stat-value">{shown(officers.length)}</p></Card>
        <Card className="stat"><p className="stat-label">Present</p><p className="stat-value" style={{ color: counts.PRESENT ? "var(--color-healthy)" : undefined }}>{shown(counts.PRESENT)}</p></Card>
        <Card className="stat"><p className="stat-label">Checked out</p><p className="stat-value">{shown(counts.CHECKED_OUT)}</p></Card>
        <Card className="stat"><p className="stat-label">Yet to arrive</p><p className="stat-value" style={{ color: counts.YET_TO_ARRIVE ? "var(--color-warning)" : undefined }}>{shown(counts.YET_TO_ARRIVE)}</p></Card>
        <Card className="stat"><p className="stat-label">Absent</p><p className="stat-value" style={{ color: counts.ABSENT ? "var(--color-danger)" : undefined }}>{shown(counts.ABSENT)}</p></Card>
      </div>

      <Card>
        <SectionHeader title="Officer registry" />
        <div className="off-body">
          {error && <p role="alert" style={{ color: "var(--color-danger)" }}>{error}</p>}
          <table>
            <thead>
              <tr><th>Officer</th><th>Checkpoint</th><th>Card</th><th>Fingerprint</th><th>Status today</th><th className="num">In</th><th className="num">Out</th></tr>
            </thead>
            <tbody>
              {officers.map((o) => {
                const st = STATES.find((s) => s.key === stateOf(o))!;
                return (
                  <tr key={o.id}>
                    <td>{o.name}<span className="scan-sub">{o.employee_id}</span></td>
                    <td>{o.checkpoints.length ? o.checkpoints.join(", ") : "Any"}</td>
                    <td className="t-mono">{o.rfid_uid ?? "—"}</td>
                    <td className="t-mono">{o.fingerprint_page_id ?? "—"}</td>
                    <td><StatusBadge label={st.label} tone={st.tone} /></td>
                    <td className="num t-mono">{clock(o.entry_at)}</td>
                    <td className="num t-mono">{clock(o.exit_at)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          {!loading && officers.length === 0 && !error && <p className="scan-empty">No officers are registered yet.</p>}
        </div>
      </Card>

      <Card>
        <SectionHeader title="Proxy attempts" />
        <div className="off-body">
          <p>A card was tapped, but the fingerprint presented within the window belonged to someone else (or no enrolled finger at all). Shown here instead of being silently dropped.</p>
          <table>
            <thead>
              <tr><th>Checkpoint</th><th>Card claimed</th><th>Finger actually matched</th><th className="num">Score</th><th className="num">When</th></tr>
            </thead>
            <tbody>
              {proxyAttempts.map((e) => (
                <tr key={e.id}>
                  <td>{e.checkpoint_id ?? e.node_id}</td>
                  <td>{e.claimed_name ?? e.claimed_employee_id ?? e.claimed_uid}</td>
                  <td>{e.actual_name ?? e.actual_employee_id ?? (e.actual_page_id === null ? "—" : e.actual_page_id === 65535 ? "none presented" : `page ${e.actual_page_id}`)}</td>
                  <td className="num t-mono">{e.score ?? "—"}</td>
                  <td className="num t-mono">{clock(e.timestamp)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {proxyAttempts.length === 0 && <p className="scan-empty">No proxy attempts recorded.</p>}
        </div>
      </Card>

      <dl className="off-basis">
        <dt>How status is decided</dt>
        <dd>
          {STATES.map((s) => <span key={s.key}><b>{s.label}</b>: {s.help}. </span>)}
          The day runs on {tz || "the configured timezone"}; the cut-off is {cutoff}. A card tap alone does not mark attendance -- the officer must also present
          their enrolled fingerprint at the same checkpoint within the verification window. The first such verified visit of the day is the check-in, a later
          one (at least 2 minutes after) is the check-out, and a read at a checkpoint that is not the officer&apos;s own is not counted.
        </dd>
      </dl>
    </div>
  );
}
