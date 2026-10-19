#!/usr/bin/env python3
"""Minimal resumable macOS audio-review helper for the Phase 4.2 queue.

Usage:
  python3 review_tool.py --reviewer reviewer1

The tool writes a separate review_results.csv. It never edits the candidate
manifest or review queue. Audio is played with macOS `afplay` when available.
"""
import argparse
import csv
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path


HERE = Path(__file__).parents[2]
QUEUE = HERE / "datasets/phase4_2_candidate/review_queue.csv"
RESULTS = HERE / "datasets/phase4_2_candidate/review_results.csv"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--reviewer", required=True)
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()
    rows = list(csv.DictReader(QUEUE.open(newline="")))
    existing = {}
    if RESULTS.exists():
        existing = {r["candidate_id"]: r for r in csv.DictReader(RESULTS.open(newline=""))}
    pending = [r for r in rows if r["candidate_id"] not in existing]
    if args.limit:
        pending = pending[: args.limit]
    fields = list(rows[0]) + ["reviewer_id", "review_decision", "label_confidence", "event_audible", "partial_or_low_energy", "event_start_s", "event_end_s", "multiple_event_classes", "ambiguity_notes", "review_timestamp_utc"]
    for row in pending:
        print(f"\n{row['candidate_id']} | {row['source_dataset']} | proposed={row['original_label']} | priority={row['review_priority']}")
        print(row["audio_path"])
        if shutil.which("afplay") and Path(row["audio_path"]).exists():
            subprocess.run(["afplay", row["audio_path"]], check=False)
        decision = input("Decision [a accepted, r relabel, m ambiguous, x exclude, s second review, q quit]: ").strip().lower()
        if decision == "q":
            break
        mapped = {"a": "ACCEPTED", "r": "RELABEL_REQUIRED", "m": "AMBIGUOUS", "x": "EXCLUDED", "s": "NEEDS_SECOND_REVIEW"}.get(decision, "AMBIGUOUS")
        out = dict(row)
        out.update({
            "reviewer_id": args.reviewer,
            "review_decision": mapped,
            "label_confidence": input("Confidence [high/medium/low]: ").strip(),
            "event_audible": input("Event audible [YES/NO/UNCERTAIN]: ").strip().upper(),
            "partial_or_low_energy": input("Partial/low-energy [YES/NO/UNKNOWN]: ").strip().upper(),
            "event_start_s": input("Start seconds (blank if unknown): ").strip(),
            "event_end_s": input("End seconds (blank if unknown): ").strip(),
            "multiple_event_classes": input("Multiple event classes [YES/NO/UNKNOWN]: ").strip().upper(),
            "ambiguity_notes": input("Notes: ").strip(),
            "review_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        })
        existing[row["candidate_id"]] = out
        with RESULTS.open("w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()
            writer.writerows(existing.values())
        print(f"Saved {mapped}; {len(existing)} total reviewed.")


if __name__ == "__main__":
    main()
