"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { fetchAcousticEvents, AcousticEvent } from "../../../lib/api";
import { Card } from "../../../components/ui/Card";
import { SectionHeader } from "../../../components/ui/SectionHeader";
import { StatusBadge } from "../../../components/ui/StatusBadge";
import { useForestWebSocket } from "../../../lib/ws";

const CLASSIFICATION_COLORS: Record<string, { bg: string; border: string; text: string }> = {
  Gunshot:     { bg: "#fef2f2", border: "#fecaca", text: "#991b1b" },
  Chainsaw:    { bg: "#fffbeb", border: "#fde68a", text: "#92400e" },
  "Non-threat": { bg: "#f0fdf4", border: "#bbf7d0", text: "#15803d" },
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
    <div className="dashboard-page" style={{ padding: "1.5rem" }}>
      <header className="page-header" style={{ marginBottom: "1.5rem" }}>
        <h1 style={{ fontSize: "1.75rem", fontWeight: 700, color: "var(--color-navy)" }}>Acoustic Threat Review Queue</h1>
        <p style={{ color: "#64748b", marginTop: "4px" }}>
          Edge-classified acoustic events (Gunshot, Chainsaw, Non-threat) detected by TinyML field nodes. Review, confirm, or dismiss each event.
        </p>
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
              border: filter === f ? "2px solid var(--color-navy)" : "2px solid #e2e8f0",
              background: filter === f ? "var(--color-navy)" : "#f8fafc",
              color: filter === f ? "#fff" : "#475569",
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
            <div style={{ textAlign: "center", padding: "2rem", color: "#64748b" }}>
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
                        <span style={{ fontSize: "0.85rem", fontWeight: 700, color: "#475569" }}>
                          {Math.round(evt.confidence * 100)}% confidence
                        </span>
                        <StatusBadge label={evt.reviewStatus} tone={evt.reviewStatus === "CONFIRMED" ? "danger" : evt.reviewStatus === "PENDING_REVIEW" ? "warning" : "healthy"} />
                      </div>
                      <div style={{ marginTop: "6px", fontSize: "0.85rem", color: "#475569", display: "flex", gap: "1.5rem", flexWrap: "wrap" }}>
                        <span><strong>Event ID:</strong> {evt.eventId}</span>
                        <span><strong>Node:</strong> {evt.nodeId}</span>
                        <span><strong>Zone:</strong> {evt.zone}</span>
                        <span><strong>Time:</strong> {evt.timestamp}</span>
                        {evt.modelVersion && <span><strong>Model:</strong> {evt.modelVersion}</span>}
                      </div>
                      <div style={{ marginTop: "4px", fontSize: "0.8rem", color: "#64748b", display: "flex", gap: "1rem" }}>
                        <span>Signature: <StatusBadge label={evt.signatureStatus === "PENDING" ? "UNSIGNED (pending review)" : evt.signatureStatus} tone={evt.signatureStatus === "VALID" ? "healthy" : evt.signatureStatus === "PENDING" ? "warning" : "danger"} /></span>
                        <span>Sync: <StatusBadge label={evt.syncStatus} tone={evt.syncStatus === "SYNCED" ? "healthy" : "warning"} /></span>
                        <span>Audio Clip: {evt.clipAvailable ? <span style={{ color: "#16a34a" }}>Available</span> : <span style={{ color: "#94a3b8" }}>Not stored</span>}</span>
                      </div>
                    </div>
                    <Link
                      href={`/dashboard/acoustic-events/${evt.id}`}
                      style={{
                        padding: "8px 16px",
                        fontSize: "0.85rem",
                        fontWeight: 600,
                        color: "#0369a1",
                        border: "1px solid #bae6fd",
                        borderRadius: "6px",
                        background: "#f0f9ff",
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
