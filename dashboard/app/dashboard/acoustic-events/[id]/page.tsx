"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { fetchAcousticEventById, reviewAcousticEvent, AcousticEvent, ReviewDecision } from "../../../../lib/api";
import { Card } from "../../../../components/ui/Card";
import { StatusBadge } from "../../../../components/ui/StatusBadge";

export default function AcousticEventDetailPage() {
  const params = useParams();
  const [event, setEvent] = useState<AcousticEvent | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState<ReviewDecision | null>(null);
  const [notice, setNotice] = useState<{ ok: boolean; text: string } | null>(null);

  useEffect(() => {
    async function load() {
      const id = typeof params.id === "string" ? params.id : params.id?.[0] || "";
      const data = await fetchAcousticEventById(id);
      setEvent(data);
      setLoading(false);
    }
    load();
  }, [params.id]);

  async function decide(decision: ReviewDecision, done: string) {
    if (!event) return;
    setSaving(decision);
    setNotice(null);
    try {
      setEvent(await reviewAcousticEvent(event.eventId, decision));
      setNotice({ ok: true, text: done });
    } catch (e) {
      setNotice({ ok: false, text: e instanceof Error ? e.message : "Could not save the review" });
    } finally {
      setSaving(null);
    }
  }

  if (loading) return <div style={{ padding: "2rem" }}>Loading acoustic event...</div>;
  if (!event) return <div style={{ padding: "2rem" }}>Event not found.</div>;

  const isThreat = event.classification === "Gunshot" || event.classification === "Chainsaw";
  const reviewColors: Record<string, string> = {
    PENDING_REVIEW: "var(--color-warning)",
    DETECTED: "var(--color-forest-dark)",
    REVIEWED: "var(--color-healthy)",
    DISMISSED: "var(--color-muted)",
    CONFIRMED: "var(--color-danger)",
  };

  return (
    <div className="dashboard-page" style={{ padding: "1.5rem", maxWidth: "860px" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1.5rem" }}>
        <div>
          <Link href="/dashboard/acoustic-events" style={{ color: "var(--color-muted)", fontSize: "0.85rem", textDecoration: "none" }}>
            ← Back to Acoustic Threat Queue
          </Link>
          <h1>
            Acoustic Event — {event.eventId}
          </h1>
        </div>
      </div>

      {/* CLASSIFICATION BANNER */}
      <Card style={{ marginBottom: "1.5rem", padding: "1.25rem", background: isThreat ? "var(--color-danger-bg)" : "var(--color-healthy-bg)" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <div>
            <h2 style={{ fontSize: "1.3rem", fontWeight: 700, color: isThreat ? "var(--color-danger)" : "var(--color-healthy)" }}>
              Classification: {event.classification}
            </h2>
            <p style={{ fontSize: "0.85rem", color: "var(--color-text-soft)", marginTop: "4px" }}>
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
        <h3 style={{ padding: "1rem 1rem 0.5rem", fontWeight: 700, color: "var(--color-navy)", borderBottom: "1px solid var(--color-border)" }}>Event Information</h3>
        <table>
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
              <tr key={String(label)}>
                <td>{label}</td>
                <td>{value}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>

      {/* REVIEW */}
      <Card style={{ marginBottom: "1.5rem" }}>
        <h3 style={{ padding: "1rem 1rem 0.5rem", fontWeight: 700, color: "var(--color-navy)", borderBottom: "1px solid var(--color-border)" }}>Review this detection</h3>
        <div className="review-body">
          <p className="review-lead">
            The node classified this sound on the device. Nobody has heard it, so decide from the confidence, the time and whether a patrol was at
            the checkpoint. Your decision is recorded next to the detection; the original classification is never changed.
          </p>
          <div className="review-actions">
            <button type="button" className="review-btn review-btn-danger" disabled={saving !== null || event.reviewStatus === "CONFIRMED"}
              onClick={() => decide("CONFIRMED", `Confirmed as a real ${event.classification.toLowerCase()} event.`)}>
              {saving === "CONFIRMED" ? "Saving..." : `Confirm real ${event.classification.toLowerCase()}`}
            </button>
            <button type="button" className="review-btn" disabled={saving !== null || event.reviewStatus === "DISMISSED"}
              onClick={() => decide("DISMISSED", "Dismissed as a false alarm.")}>
              {saving === "DISMISSED" ? "Saving..." : "False alarm (not a " + event.classification.toLowerCase() + ")"}
            </button>
            <button type="button" className="review-btn" disabled={saving !== null || event.reviewStatus === "REVIEWED"}
              onClick={() => decide("REVIEWED", "Marked as reviewed, outcome unclear.")}>
              {saving === "REVIEWED" ? "Saving..." : "Reviewed, unclear"}
            </button>
            {event.reviewStatus !== "PENDING_REVIEW" && (
              <button type="button" className="review-btn review-btn-quiet" disabled={saving !== null}
                onClick={() => decide("PENDING_REVIEW", "Moved back to the review queue.")}>
                Reopen
              </button>
            )}
          </div>
          {notice && <p role="status" className={notice.ok ? "review-note review-note-ok" : "review-note review-note-bad"}>{notice.text}</p>}
          <dl className="review-help">
            <dt>Confirm</dt><dd>It really was that sound. It stays in the record as a confirmed threat.</dd>
            <dt>False alarm</dt><dd>It was something else (wind, voices, an engine, rain). It stays in the history as dismissed, so false-alarm patterns stay visible.</dd>
            <dt>Reviewed, unclear</dt><dd>You looked at it and cannot tell.</dd>
          </dl>
          <p className="review-limit">
            <strong>No audio is available.</strong> The node does not send sound over LoRa. One second of audio is about 32 KB, a packet here carries at
            most 48 bytes, and at roughly 5 kbps that is over 45 seconds of airtime for one second of sound. Only the class and confidence travel.
          </p>
        </div>
      </Card>

      {/* INTEGRITY */}
      <Card>
        <h3 style={{ padding: "1rem 1rem 0.5rem", fontWeight: 700, color: "var(--color-navy)", borderBottom: "1px solid var(--color-border)" }}>Record Integrity</h3>
        <div style={{ padding: "1rem", display: "flex", gap: "2rem", flexWrap: "wrap" }}>
          <div>
            <span style={{ fontSize: "0.8rem", fontWeight: 600, color: "var(--color-muted)", display: "block", marginBottom: "4px" }}>Signature</span>
            <StatusBadge label={event.signatureStatus === "PENDING" ? "UNSIGNED (pending review)" : event.signatureStatus} tone={event.signatureStatus === "VALID" ? "healthy" : event.signatureStatus === "PENDING" ? "warning" : "danger"} />
          </div>
          <div>
            <span style={{ fontSize: "0.8rem", fontWeight: 600, color: "var(--color-muted)", display: "block", marginBottom: "4px" }}>Sync Status</span>
            <StatusBadge label={event.syncStatus} tone={event.syncStatus === "SYNCED" ? "healthy" : "warning"} />
          </div>
        </div>
      </Card>
    </div>
  );
}
