"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { fetchAcousticEvents } from "../../lib/api";
import { fetchRfidEvents } from "../../lib/rfidApi";

type Tone = "healthy" | "warning" | "danger";
type Note = { key: string; tone: Tone; title: string; detail: string; href: string; at: number };

const COLORS: Record<Tone, string> = { healthy: "#22c55e", warning: "#f59e0b", danger: "#ef4444" };
const POLL_MS = 5000;
const TOAST_MS = 8000;
const MAX_KEPT = 30;

export function Notifications() {
  const seen = useRef<Set<string>>(new Set());
  const primed = useRef(false);
  const [notes, setNotes] = useState<Note[]>([]);
  const [toasts, setToasts] = useState<Note[]>([]);
  const [unread, setUnread] = useState(0);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    let alive = true;
    async function poll() {
      const [rfid, acoustic] = await Promise.all([
        fetchRfidEvents().catch(() => null),
        fetchAcousticEvents().catch(() => null),
      ]);
      if (!alive) return;
      const fresh: Note[] = [];
      for (const e of rfid ?? []) {
        const key = `r:${e.id}`;
        if (seen.current.has(key)) continue;
        seen.current.add(key);
        if (e.status === "AUTHORIZED") fresh.push({ key, tone: "healthy", title: "Attendance recorded", detail: `${e.employee_id ?? e.uid} at ${e.checkpoint_id ?? e.node_id}`, href: "/dashboard/rfid-events", at: Date.parse(e.timestamp) });
        else if (e.status === "INVALID") fresh.push({ key, tone: "danger", title: "Invalid checkpoint access", detail: e.reason ?? `${e.employee_id ?? e.uid} at ${e.checkpoint_id ?? e.node_id}`, href: "/dashboard/rfid-events", at: Date.parse(e.timestamp) });
        else fresh.push({ key, tone: "warning", title: "Unknown card scanned", detail: `${e.uid} at ${e.checkpoint_id ?? e.node_id}`, href: "/dashboard/rfid-events", at: Date.parse(e.timestamp) });
      }
      for (const a of acoustic ?? []) {
        const key = `a:${a.id}`;
        if (seen.current.has(key)) continue;
        seen.current.add(key);
        fresh.push({ key, tone: "danger", title: `Acoustic alert: ${a.classification}`, detail: `${Math.round(a.confidence * 100)}% at ${a.checkpointId || a.nodeId}`, href: `/dashboard/acoustic-events/${a.id}`, at: Date.parse(a.timestamp) });
      }
      // The first poll only establishes the baseline; existing history is not "new".
      if (!primed.current) { primed.current = rfid !== null || acoustic !== null; return; }
      if (!fresh.length) return;
      fresh.sort((x, y) => y.at - x.at);
      setNotes((n) => [...fresh, ...n].slice(0, MAX_KEPT));
      setUnread((u) => u + fresh.length);
      setToasts((t) => [...fresh.slice(0, 3), ...t].slice(0, 4));
      for (const f of fresh.slice(0, 3)) setTimeout(() => alive && setToasts((t) => t.filter((x) => x.key !== f.key)), TOAST_MS);
    }
    poll();
    const id = setInterval(poll, POLL_MS);
    return () => { alive = false; clearInterval(id); };
  }, []);

  return (
    <>
      <div style={{ position: "relative" }}>
        <button type="button" aria-label={`Notifications, ${unread} unread`} onClick={() => { setOpen((o) => !o); setUnread(0); }}
          style={{ position: "relative", background: "transparent", border: "1px solid #cbd5e1", borderRadius: 6, padding: "4px 8px", cursor: "pointer", fontSize: "1rem" }}>
          🔔
          {unread > 0 && <span style={{ position: "absolute", top: -6, right: -6, background: "#ef4444", color: "#fff", borderRadius: 999, fontSize: 11, fontWeight: 700, padding: "1px 6px" }}>{unread}</span>}
        </button>
        {open && (
          <div role="dialog" aria-label="Notifications" style={{ position: "absolute", right: 0, top: "calc(100% + 8px)", width: 340, maxHeight: 420, overflowY: "auto", background: "#0f172a", color: "#e2e8f0", border: "1px solid #334155", borderRadius: 8, boxShadow: "0 12px 32px rgba(0,0,0,.4)", zIndex: 1000 }}>
            {notes.length === 0 && <div style={{ padding: 16, fontSize: 13, opacity: 0.7 }}>No new activity since you opened the dashboard.</div>}
            {notes.map((n) => (
              <Link key={n.key} href={n.href} onClick={() => setOpen(false)} style={{ display: "block", padding: "10px 14px", borderLeft: `4px solid ${COLORS[n.tone]}`, borderBottom: "1px solid #1e293b", textDecoration: "none", color: "inherit" }}>
                <div style={{ fontWeight: 600, fontSize: 13 }}>{n.title}</div>
                <div style={{ fontSize: 12, opacity: 0.75 }}>{n.detail}</div>
              </Link>
            ))}
          </div>
        )}
      </div>
      <div aria-live="polite" style={{ position: "fixed", right: 16, bottom: 16, display: "grid", gap: 8, zIndex: 1100, width: 320 }}>
        {toasts.map((n) => (
          <Link key={n.key} href={n.href} style={{ display: "block", padding: "10px 14px", background: "#0f172a", color: "#e2e8f0", borderLeft: `4px solid ${COLORS[n.tone]}`, borderRadius: 6, boxShadow: "0 8px 24px rgba(0,0,0,.35)", textDecoration: "none" }}>
            <div style={{ fontWeight: 600, fontSize: 13 }}>{n.title}</div>
            <div style={{ fontSize: 12, opacity: 0.8 }}>{n.detail}</div>
          </Link>
        ))}
      </div>
    </>
  );
}
