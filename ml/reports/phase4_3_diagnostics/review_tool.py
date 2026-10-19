#!/usr/bin/env python3
"""Local, resumable reviewer for the Phase 4.3 candidate queue."""

import argparse
import csv
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).parents[2]
DEFAULT_QUEUE = ROOT / "datasets/phase4_3_candidate/review_queue.csv"
DEFAULT_OUTPUT = ROOT / "datasets/phase4_3_candidate/review_decisions.csv"
DECISIONS = ("ACCEPTED", "RELABEL_REQUIRED", "AMBIGUOUS", "EXCLUDED", "NEEDS_SECOND_REVIEW")
KEY_TO_DECISION = {"a": "ACCEPTED", "r": "RELABEL_REQUIRED", "m": "AMBIGUOUS", "x": "EXCLUDED", "s": "NEEDS_SECOND_REVIEW"}
REQUIRED_QUEUE_COLUMNS = {"candidate_id", "source_recording_id", "source_dataset", "audio_path", "content_sha256", "parent_recording_id", "original_label"}
REQUIRED_DECISION_COLUMNS = {"candidate_id", "decision"}


def read_csv(path):
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        return list(reader), list(reader.fieldnames or [])


def is_completed(row):
    return (str(row.get("decision", "")).strip() in DECISIONS
            and bool(str(row.get("reviewer_id", "")).strip())
            and bool(str(row.get("review_timestamp_utc", "")).strip()))


def validate_inputs(queue, queue_fields, decisions, decision_fields):
    missing_queue = REQUIRED_QUEUE_COLUMNS - set(queue_fields)
    missing_decisions = REQUIRED_DECISION_COLUMNS - set(decision_fields)
    if missing_queue:
        raise SystemExit(f"Queue is missing required columns: {sorted(missing_queue)}")
    if missing_decisions:
        raise SystemExit(f"Decisions file is missing required columns: {sorted(missing_decisions)}")
    queue_ids = [row["candidate_id"] for row in queue]
    if len(queue_ids) != len(set(queue_ids)):
        raise SystemExit("Refusing to run: duplicate candidate IDs in review queue")
    decision_ids = [row["candidate_id"] for row in decisions]
    if len(decision_ids) != len(set(decision_ids)):
        raise SystemExit("Refusing to run: duplicate candidate IDs in decisions file")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--reviewer", required=True)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--queue", type=Path, default=DEFAULT_QUEUE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--no-play", action="store_true", help="Skip afplay for smoke tests")
    args = parser.parse_args()

    queue, queue_fields = read_csv(args.queue)
    decisions, decision_fields = read_csv(args.output) if args.output.exists() else ([], [])
    validate_inputs(queue, queue_fields, decisions, decision_fields or ["candidate_id", "decision"])

    existing_by_id = {}
    for row in decisions:
        candidate_id = row["candidate_id"]
        if candidate_id in existing_by_id:
            raise SystemExit(f"Refusing to run: duplicate decision for {candidate_id}")
        existing_by_id[candidate_id] = row

    # PENDING, blank, or missing decisions remain reviewable.
    pending = [row for row in queue if not is_completed(existing_by_id.get(row["candidate_id"], {}))]
    if args.limit:
        pending = pending[:args.limit]
    fields = list(dict.fromkeys(list(decision_fields or ["candidate_id", "decision"]) + queue_fields))
    print(f"Loaded {len(queue)} queue candidates; {len(pending)} pending candidates eligible for review.")

    for item in pending:
        proposed_label = item.get("original_label", item.get("proposed_label", ""))
        print(f"\n{item['candidate_id']} | {item.get('source_dataset', '')} | proposed={proposed_label} | {item.get('batch_membership', '')}")
        print(item.get("audio_path", ""))
        audio_path = Path(item.get("audio_path", ""))
        if not args.no_play and shutil.which("afplay") and audio_path.exists():
            subprocess.run(["afplay", str(audio_path)], check=False)
        key = input("Decision [a/r/m/x/s, q=quit]: ").strip().lower()
        if key == "q":
            break
        if key not in KEY_TO_DECISION:
            print("Skipped; no decision recorded.")
            continue

        decision = KEY_TO_DECISION[key]
        row = dict(existing_by_id.get(item["candidate_id"], {}))
        row.update(item)
        row["proposed_label"] = proposed_label
        row.update({
            "human_verified_label": input("Human label (blank if not assigned): ").strip(),
            "reviewer_id": args.reviewer,
            "review_timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "label_confidence": input("Confidence [high/medium/low]: ").strip(),
            "target_event_audible": input("Event audible [YES/NO/UNCERTAIN]: ").strip().upper(),
            "event_start_s": input("Start seconds (blank if unknown): ").strip(),
            "event_end_s": input("End seconds (blank if unknown): ").strip(),
            "partial_or_low_energy": input("Partial/low-energy [YES/NO/UNKNOWN]: ").strip().upper(),
            "multi_event_indicator": input("Multiple event classes [YES/NO/UNKNOWN]: ").strip().upper(),
            "ambiguity_notes": input("Notes: ").strip(),
            "decision": decision,
            "review_decision": decision,
            "review_status": decision,
            "exclusion_reason": input("Exclusion reason (blank if none): ").strip(),
        })
        existing_by_id[item["candidate_id"]] = row

        output_rows = []
        for queue_row in queue:
            candidate_id = queue_row["candidate_id"]
            saved = dict(existing_by_id.get(candidate_id, {}))
            for key_name, value in queue_row.items():
                if key_name not in saved or not str(saved[key_name]).strip():
                    saved[key_name] = value
            output_rows.append({field: saved.get(field, "") for field in fields})
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(output_rows)
        completed = sum(is_completed(saved) for saved in output_rows)
        print(f"Saved {decision}; completed human decisions: {completed}; pending remaining: {len(queue) - completed}")


if __name__ == "__main__":
    main()
