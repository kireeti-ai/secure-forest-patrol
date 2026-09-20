"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { fetchAcousticEvents } from "../../lib/api";
import { fetchRfidEvents } from "../../lib/rfidApi";

type Tone = "healthy" | "warning" | "danger";
type Note = { key: string; tone: Tone; tag: string; title: string; detail: string; href: string; at: number };

const clock = (t: number) => (Number.isFinite(t) ? new Date(t).toLocaleTimeString([], { hour12: false }) : "");

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
        if (e.status === "AUTHORIZED") fresh.push({ key, tone: "healthy", tag: "ATTENDANCE", title: "Checked in", detail: `${e.employee_id ?? e.uid} at ${e.checkpoint_id ?? e.node_id}`, href: "/dashboard/rfid-events", at: Date.parse(e.timestamp) });
        else if (e.status === "INVALID") fresh.push({ key, tone: "danger", tag: "INVALID", title: "Wrong checkpoint", detail: e.reason ?? `${e.employee_id ?? e.uid} at ${e.checkpoint_id ?? e.node_id}`, href: "/dashboard/rfid-events", at: Date.parse(e.timestamp) });
        else fresh.push({ key, tone: "warning", tag: "UNKNOWN", title: "Unregistered card", detail: `${e.uid} at ${e.checkpoint_id ?? e.node_id}`, href: "/dashboard/rfid-events", at: Date.parse(e.timestamp) });
      }
      for (const a of acoustic ?? []) {
        const key = `a:${a.id}`;
        if (seen.current.has(key)) continue;
        seen.current.add(key);
        fresh.push({ key, tone: "danger", tag: "ACOUSTIC", title: a.classification, detail: `${Math.round(a.confidence * 100)}% at ${a.checkpointId || a.nodeId}`, href: `/dashboard/acoustic-events/${a.id}`, at: Date.parse(a.timestamp) });
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
      <div className="alerts">
        <button type="button" className="alerts-button" aria-expanded={open} aria-label={`Alerts, ${unread} unread`}
          onClick={() => { setOpen((o) => !o); setUnread(0); }}>
          Alerts
          {unread > 0 && <span className="alerts-count">{unread}</span>}
        </button>
        {open && (
          <div className="alerts-panel" role="dialog" aria-label="Alerts">
            <div className="alerts-head"><span>Since you opened the dashboard</span><span>{notes.length}</span></div>
            {notes.length === 0 && <div className="alerts-empty">Nothing new. Scans and detections appear here as they arrive.</div>}
            {notes.map((n) => (
              <Link key={n.key} href={n.href} onClick={() => setOpen(false)} className="alert-row">
                <span className="alert-time">{clock(n.at)}</span>
                <span>
                  <span className="alert-title"><span className={`alert-tag alert-tag-${n.tone}`}>{n.tag}</span>{n.title}</span>
                  <span className="alert-detail" style={{ display: "block" }}>{n.detail}</span>
                </span>
              </Link>
            ))}
          </div>
        )}
      </div>
      <div className="toast-stack" aria-live="polite">
        {toasts.map((n) => (
          <Link key={n.key} href={n.href} className="toast">
            <span className="alert-title"><span className={`alert-tag alert-tag-${n.tone}`}>{n.tag}</span>{n.title}</span>
            <span className="alert-detail" style={{ display: "block" }}>{n.detail}</span>
          </Link>
        ))}
      </div>
    </>
  );
}
