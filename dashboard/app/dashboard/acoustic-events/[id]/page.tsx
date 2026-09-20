"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { fetchAcousticEventById, AcousticEvent } from "../../../../lib/api";
import { Card } from "../../../../components/ui/Card";
import { StatusBadge } from "../../../../components/ui/StatusBadge";

export default function AcousticEventDetailPage() {
  const params = useParams();
  const [event, setEvent] = useState<AcousticEvent | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      const id = typeof params.id === "string" ? params.id : params.id?.[0] || "";
      const data = await fetchAcousticEventById(id);
      setEvent(data);
      setLoading(false);
    }
    load();
  }, [params.id]);

  if (loading) return <div style={{ padding: "2rem" }}>Loading acoustic event...</div>;
  if (!event) return <div style={{ padding: "2rem" }}>Event not found.</div>;

  const isThreat = event.classification === "Gunshot" || event.classification === "Chainsaw";
  const reviewColors: Record<string, string> = {
    PENDING_REVIEW: "#d97706",
    DETECTED: "#0369a1",
    REVIEWED: "#16a34a",
    DISMISSED: "#64748b",
    CONFIRMED: "#dc2626",
  };

  return (
    <div className="dashboard-page" style={{ padding: "1.5rem", maxWidth: "860px" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1.5rem" }}>
        <div>
          <Link href="/dashboard/acoustic-events" style={{ color: "#64748b", fontSize: "0.85rem", textDecoration: "none" }}>
            ← Back to Acoustic Threat Queue
          </Link>
          <h1 style={{ fontSize: "1.75rem", fontWeight: 700, color: "var(--color-navy)", marginTop: "6px" }}>
            Acoustic Event — {event.eventId}
          </h1>
        </div>
      </div>

      {/* CLASSIFICATION BANNER */}
      <Card style={{ marginBottom: "1.5rem", padding: "1.25rem", background: isThreat ? "#fef2f2" : "#f0fdf4", borderLeft: `4px solid ${isThreat ? "#dc2626" : "#16a34a"}` }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <div>
            <h2 style={{ fontSize: "1.3rem", fontWeight: 700, color: isThreat ? "#991b1b" : "#15803d" }}>
              {isThreat ? "⚠" : "✓"} Edge Classification: {event.classification}
            </h2>
            <p style={{ fontSize: "0.85rem", color: "#475569", marginTop: "4px" }}>
              TinyML on-device inference confidence: <strong>{Math.round(event.confidence * 100)}%</strong>
              {event.modelVersion && ` — Model: ${event.modelVersion}`}
            </p>
          </div>
          <StatusBadge
            label={event.reviewStatus}
            tone={event.reviewStatus === "CONFIRMED" ? "danger" : event.reviewStatus === "PENDING_REVIEW" ? "warning" : "healthy"}
          />
        </div>
      </Card>

      {/* EVENT DETAILS */}
      <Card style={{ marginBottom: "1.5rem" }}>
        <h3 style={{ padding: "1rem 1rem 0.5rem", fontWeight: 700, color: "var(--color-navy)", borderBottom: "1px solid #e2e8f0" }}>Event Information</h3>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.9rem" }}>
          <tbody>
            {[
              ["Event ID", event.eventId],
              ["Node ID", <code key="n">{event.nodeId}</code>],
              ["Checkpoint ID", event.checkpointId],
              ["Zone", event.zone],
              ["Detection Timestamp", event.timestamp],
              ["Classification", event.classification],
              ["Confidence Score", `${Math.round(event.confidence * 100)}%`],
              ["Audio Clip Stored", event.clipAvailable ? "Yes — Available for manual review" : "No — Edge clip not retained"],
            ].map(([label, value]) => (
              <tr key={String(label)} style={{ borderBottom: "1px solid #f1f5f9" }}>
                <td style={{ padding: "10px 16px", color: "#64748b", fontWeight: 600, width: "200px" }}>{label}</td>
                <td style={{ padding: "10px 16px", color: "#0f172a" }}>{value}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>

      {/* REVIEW WORKFLOW */}
      <Card style={{ marginBottom: "1.5rem" }}>
        <h3 style={{ padding: "1rem 1rem 0.5rem", fontWeight: 700, color: "var(--color-navy)", borderBottom: "1px solid #e2e8f0" }}>Review Workflow State</h3>
        <div style={{ padding: "1rem", display: "flex", alignItems: "center", gap: "1rem", flexWrap: "wrap" }}>
          {(["DETECTED", "PENDING_REVIEW", "REVIEWED", "CONFIRMED", "DISMISSED"] as const).map((state, i, arr) => (
            <>
              <div
                key={state}
                style={{
                  padding: "8px 16px",
                  borderRadius: "24px",
                  fontWeight: 700,
                  fontSize: "0.85rem",
                  background: event.reviewStatus === state ? reviewColors[state] : "#f1f5f9",
                  color: event.reviewStatus === state ? "#fff" : "#64748b",
                  border: `2px solid ${event.reviewStatus === state ? reviewColors[state] : "#e2e8f0"}`,
                }}
              >
                {state.replace("_", " ")}
              </div>
              {i < arr.length - 1 && <span style={{ color: "#cbd5e1", fontSize: "1rem" }}>→</span>}
            </>
          ))}
        </div>
      </Card>

      {/* INTEGRITY */}
      <Card>
        <h3 style={{ padding: "1rem 1rem 0.5rem", fontWeight: 700, color: "var(--color-navy)", borderBottom: "1px solid #e2e8f0" }}>Record Integrity</h3>
        <div style={{ padding: "1rem", display: "flex", gap: "2rem", flexWrap: "wrap" }}>
          <div>
            <span style={{ fontSize: "0.8rem", fontWeight: 600, color: "#64748b", display: "block", marginBottom: "4px" }}>Signature</span>
            <StatusBadge label={event.signatureStatus === "PENDING" ? "UNSIGNED (pending review)" : event.signatureStatus} tone={event.signatureStatus === "VALID" ? "healthy" : event.signatureStatus === "PENDING" ? "warning" : "danger"} />
          </div>
          <div>
            <span style={{ fontSize: "0.8rem", fontWeight: 600, color: "#64748b", display: "block", marginBottom: "4px" }}>Sync Status</span>
            <StatusBadge label={event.syncStatus} tone={event.syncStatus === "SYNCED" ? "healthy" : "warning"} />
          </div>
        </div>
      </Card>
    </div>
  );
}
