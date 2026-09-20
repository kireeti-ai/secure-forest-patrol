"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { fetchAcousticEvents, AcousticEvent } from "../../../lib/api";
import { Card } from "../../../components/ui/Card";
import { SectionHeader } from "../../../components/ui/SectionHeader";
import { StatusBadge } from "../../../components/ui/StatusBadge";
import { useForestWebSocket } from "../../../lib/ws";

const CLASSIFICATION_COLORS: Record<string, { bg: string; border: string; text: string }> = {
  Gunshot:     { bg: "var(--color-danger-bg)", border: "var(--color-border)", text: "var(--color-danger)" },
  Chainsaw:    { bg: "var(--color-warning-bg)", border: "var(--color-border)", text: "var(--color-warning)" },
  "Non-threat": { bg: "var(--color-healthy-bg)", border: "var(--color-border)", text: "var(--color-healthy)" },
};

export default function AcousticEventsPage() {
  const [events, setEvents] = useState<AcousticEvent[]>([]);
  const [filter, setFilter] = useState<string>("ALL");
  const [loading, setLoading] = useState(true);
  const loadRef = useRef<() => void>(() => {});

  useEffect(() => {
    async function load() {
      const data = await fetchAcousticEvents();
      setEvents(data);
      setLoading(false);
    }
    loadRef.current = load;
    load();
  }, []);

  useForestWebSocket(
    ["ACOUSTIC_EVENT_RECEIVED"],
    () => loadRef.current(),
    () => loadRef.current()
  );

  const filtered = filter === "ALL" ? events : events.filter((e) => e.reviewStatus === filter);

  const counters = {
    ALL: events.length,
    PENDING_REVIEW: events.filter((e) => e.reviewStatus === "PENDING_REVIEW").length,
    CONFIRMED: events.filter((e) => e.reviewStatus === "CONFIRMED").length,
    DISMISSED: events.filter((e) => e.reviewStatus === "DISMISSED").length,
  };

  return (
    <div className="dashboard-page">
      <header className="page-header">
        <h1>Acoustic events</h1>
        <p>Gunshot and chainsaw detections from field nodes, waiting for review.</p>
      </header>

      {/* FILTER TABS */}
      <div style={{ display: "flex", gap: "0.75rem", marginBottom: "1.5rem", flexWrap: "wrap" }}>
        {(["ALL", "PENDING_REVIEW", "CONFIRMED", "DISMISSED"] as const).map((f) => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            style={{
              padding: "8px 18px",
              borderRadius: "24px",
              fontWeight: 700,
              fontSize: "0.85rem",
              cursor: "pointer",
              border: filter === f ? "2px solid var(--color-navy)" : "2px solid var(--color-border)",
              background: filter === f ? "var(--color-navy)" : "var(--color-surface-alt)",
              color: filter === f ? "#fff" : "var(--color-text-soft)",
            }}
          >
            {f.replace("_", " ")} ({counters[f]})
          </button>
        ))}
      </div>

      <Card>
        <SectionHeader title={`Acoustic Events — ${filter.replace("_", " ")}`} />
        <div style={{ padding: "1rem" }}>
          {loading ? (
            <p>Loading acoustic events...</p>
          ) : filtered.length === 0 ? (
            <div style={{ textAlign: "center", padding: "2rem", color: "var(--color-muted)" }}>
              No events in this queue.
            </div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
              {filtered.map((evt) => {
                const colors = CLASSIFICATION_COLORS[evt.classification] || CLASSIFICATION_COLORS["Non-threat"];
                return (
                  <div
                    key={evt.id}
                    style={{
                      padding: "1rem 1.25rem",
                      borderRadius: "8px",
                      background: colors.bg,
                      border: `1px solid ${colors.border}`,
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "flex-start",
                      gap: "1rem",
                      flexWrap: "wrap",
                    }}
                  >
                    <div style={{ flex: 1 }}>
                      <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", flexWrap: "wrap" }}>
                        <strong style={{ fontSize: "1.05rem", color: colors.text }}>{evt.classification}</strong>
                        <span style={{ fontSize: "0.85rem", fontWeight: 700, color: "var(--color-text-soft)" }}>
                          {Math.round(evt.confidence * 100)}% confidence
                        </span>
                        <StatusBadge label={evt.reviewStatus} tone={evt.reviewStatus === "CONFIRMED" ? "danger" : evt.reviewStatus === "PENDING_REVIEW" ? "warning" : "healthy"} />
                      </div>
                      <div style={{ marginTop: "6px", fontSize: "0.85rem", color: "var(--color-text-soft)", display: "flex", gap: "1.5rem", flexWrap: "wrap" }}>
                        <span><strong>Event ID:</strong> {evt.eventId}</span>
                        <span><strong>Node:</strong> {evt.nodeId}</span>
                        <span><strong>Zone:</strong> {evt.zone}</span>
                        <span><strong>Time:</strong> {evt.timestamp}</span>
                        {evt.modelVersion && <span><strong>Model:</strong> {evt.modelVersion}</span>}
                      </div>
                      <div style={{ marginTop: "4px", fontSize: "0.8rem", color: "var(--color-muted)", display: "flex", gap: "1rem" }}>
                        <span>Signature: <StatusBadge label={evt.signatureStatus === "PENDING" ? "UNSIGNED (pending review)" : evt.signatureStatus} tone={evt.signatureStatus === "VALID" ? "healthy" : evt.signatureStatus === "PENDING" ? "warning" : "danger"} /></span>
                        <span>Sync: <StatusBadge label={evt.syncStatus} tone={evt.syncStatus === "SYNCED" ? "healthy" : "warning"} /></span>
                        <span>Audio Clip: {evt.clipAvailable ? <span style={{ color: "var(--color-healthy)" }}>Available</span> : <span style={{ color: "var(--color-faint)" }}>Not stored</span>}</span>
                      </div>
                    </div>
                    <Link
                      href={`/dashboard/acoustic-events/${evt.id}`}
                      style={{
                        padding: "8px 16px",
                        fontSize: "0.85rem",
                        fontWeight: 600,
                        color: "var(--color-forest-dark)",
                        border: "1px solid var(--color-border)",
                        borderRadius: "6px",
                        background: "var(--color-surface-alt)",
                        textDecoration: "none",
                        whiteSpace: "nowrap",
                      }}
                    >
                      Review Event →
                    </Link>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </Card>
    </div>
  );
}
