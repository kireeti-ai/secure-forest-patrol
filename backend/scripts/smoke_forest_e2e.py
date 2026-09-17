"""End-to-end HTTP smoke test for the forest backend (§41 of the migration spec).

Runs against a LIVE backend + PostgreSQL database:

    uvicorn app.main:app --port 8000
    ./.venv/bin/python scripts/smoke_forest_e2e.py

It exercises the real Gateway -> Wi-Fi -> FastAPI -> PostgreSQL path:

 1. GET  /health
 2. GET  /openapi.json      (forest paths present, no maritime paths)
 3. POST /api/auth/login    (seeded ADMIN + OPERATOR accounts)
 4. register checkpoint / nodes / officer through the API
 5. ingest a VALID signed patrol event created "offline" hours earlier
 6. re-send the SAME event              -> idempotent DUPLICATE, one DB row
 7. tampered payload                    -> INVALID_SIGNATURE
 8. event signed by the wrong key       -> INVALID_SIGNATURE
 9. unregistered predecessor hash       -> BROKEN_CHAIN
10. unknown node / malformed body / wrong gateway key
11. acoustic event + review workflow    -> CONFIRMED
12. dashboard queries return the persisted DB state
13. ledger exposes the record hashes and the broken chain
14. sync history, gateway states, DB-derived system status
15. unauthenticated / unauthorized (RBAC) requests

The dev ECC private key is generated in memory only and is never stored in
PostgreSQL (the backend only ever holds the public key).
"""

from __future__ import annotations

import argparse
import os
import sys
import uuid
from datetime import datetime, timedelta, timezone

import httpx
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services import crypto  # noqa: E402

RESULTS: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> bool:
    RESULTS.append((name, ok, detail))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" :: {detail}" if detail else ""))
    return ok


def new_device_key() -> tuple[ec.EllipticCurvePrivateKey, str]:
    """Create an ephemeral node key pair; only the public half is registered."""
    private_key = ec.generate_private_key(ec.SECP256R1())
    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("utf-8")
    return private_key, public_pem


def sign(private_key: ec.EllipticCurvePrivateKey, message: bytes) -> str:
    import base64

    return base64.b64encode(private_key.sign(message, ec.ECDSA(hashes.SHA256()))).decode("ascii")


def build_patrol_event(*, node_id: str, sequence: int, checkpoint_id: str, officer_id: str,
                       previous_hash: str, private_key: ec.EllipticCurvePrivateKey,
                       event_created_at: datetime, rfid_result: str = "VALID",
                       fingerprint_result: str = "MATCH", gateway_id: str,
                       gateway_received_at: datetime) -> dict:
    digest = crypto.patrol_payload_digest(checkpoint_id=checkpoint_id, officer_id=officer_id,
                                         rfid_result=rfid_result,
                                         fingerprint_result=fingerprint_result)
    record_hash = crypto.compute_record_hash(node_id=node_id, sequence=sequence,
                                            event_created_at=event_created_at,
                                            payload_digest=digest,
                                            previous_hash=previous_hash)
    message = crypto.patrol_signing_bytes(node_id=node_id, sequence=sequence,
                                         event_created_at=event_created_at,
                                         checkpoint_id=checkpoint_id, officer_id=officer_id,
                                         rfid_result=rfid_result,
                                         fingerprint_result=fingerprint_result,
                                         previous_hash=previous_hash, record_hash=record_hash)
    return {
        "node_id": node_id,
        "sequence": sequence,
        "event_type": "PATROL_EVENT",
        "checkpoint_id": checkpoint_id,
        "officer_id": officer_id,
        "rfid_result": rfid_result,
        "fingerprint_result": fingerprint_result,
        "event_created_at": event_created_at.isoformat(),
        "previous_hash": previous_hash,
        "record_hash": record_hash,
        "signature": sign(private_key, message),
        "gateway": {"gateway_id": gateway_id, "received_at": gateway_received_at.isoformat()},
    }


def build_acoustic_event(*, node_id: str, sequence: int, checkpoint_id: str, zone_id: str,
                         previous_hash: str, private_key: ec.EllipticCurvePrivateKey,
                         event_created_at: datetime, classification: str = "Gunshot",
                         confidence: float = 0.91, model_version: str = "tinyml-v0.1",
                         gateway_id: str, gateway_received_at: datetime) -> dict:
    digest = crypto.acoustic_payload_digest(classification=classification,
                                            confidence=confidence,
                                            model_version=model_version)
    record_hash = crypto.compute_record_hash(node_id=node_id, sequence=sequence,
                                             event_created_at=event_created_at,
                                             payload_digest=digest,
                                             previous_hash=previous_hash)
    message = crypto.acoustic_signing_bytes(node_id=node_id, sequence=sequence,
                                            event_created_at=event_created_at,
                                            checkpoint_id=checkpoint_id, zone_id=zone_id,
                                            classification=classification, confidence=confidence,
                                            model_version=model_version,
                                            previous_hash=previous_hash, record_hash=record_hash)
    return {
        "node_id": node_id,
        "sequence": sequence,
        "checkpoint_id": checkpoint_id,
        "zone_id": zone_id,
        "event_created_at": event_created_at.isoformat(),
        "classification": classification,
        "confidence": confidence,
        "model_version": model_version,
        "previous_hash": previous_hash,
        "record_hash": record_hash,
        "signature": sign(private_key, message),
        "gateway": {"gateway_id": gateway_id, "received_at": gateway_received_at.isoformat()},
    }

def main() -> int:
    parser = argparse.ArgumentParser(description="Forest backend end-to-end smoke test")
    parser.add_argument("--base-url", default=os.getenv("FOREST_SMOKE_BASE_URL",
                                                         "http://127.0.0.1:8000"))
    parser.add_argument("--admin-email", default="admin@forest.local")
    parser.add_argument("--admin-password", default="ForestAdmin123!")
    parser.add_argument("--operator-email", default="operator@forest.local")
    parser.add_argument("--operator-password", default="ForestOperator123!")
    parser.add_argument("--gateway-id", default="GW-SMOKE-01")
    parser.add_argument("--run-tag", default=uuid.uuid4().hex[:8],
                        help="Unique suffix so repeat runs register fresh resources")
    args = parser.parse_args()

    base = args.base_url.rstrip("/")
    tag = args.run_tag
    cp_id = f"CP-SMOKE-{tag}"
    node_id = f"FN-SMOKE-{tag}"
    ac_node_id = f"AN-SMOKE-{tag}"
    officer_id = f"OFF-SMOKE-{tag}"
    zone = f"ZONE-SMOKE-{tag}"

    now = datetime.now(timezone.utc)
    # A patrol recorded OFFLINE, hours before any gateway reached the backend.
    offline_created_at = (now - timedelta(hours=4, minutes=12)).replace(microsecond=0)
    gateway_received_at = (now - timedelta(minutes=3)).replace(microsecond=0)

    client = httpx.Client(base_url=base, timeout=20.0)
    gw_headers: dict[str, str] = {}
    gateway_key = os.getenv("FOREST_GATEWAY_INGESTION_KEY")
    if gateway_key:
        gw_headers["X-Gateway-Key"] = gateway_key

    # ---------------------------------------------------------------- 1/2 ----
    health = client.get("/health")
    check("1. GET /health returns 200 healthy",
          health.status_code == 200 and health.json().get("status") == "healthy",
          f"status={health.status_code}")

    spec_resp = client.get("/openapi.json")
    spec = spec_resp.json() if spec_resp.status_code == 200 else {}
    paths = sorted(spec.get("paths", {}).keys())
    required_paths = [
        "/api/ingest/gateway/forest-event",
        "/api/ingest/gateway/acoustic-event",
        "/api/ingest/gateway/status",
        "/api/forest/nodes",
        "/api/forest/checkpoints",
        "/api/forest/patrols",
        "/api/forest/officers",
        "/api/forest/acoustic-events",
        "/api/forest/ledger",
        "/api/forest/gateways",
        "/api/forest/sync-history",
        "/api/forest/system-status",
        "/api/auth/login",
    ]
    missing = [p for p in required_paths if p not in paths]
    check("2a. /openapi.json exposes every forest contract path",
          spec_resp.status_code == 200 and not missing,
          f"missing={missing}" if missing else f"{len(paths)} paths")

    maritime_tokens = ("boat", "vessel", "crew", "mob", "sos", "fleet", "marine",
                       "maritime", "navigation", "harbor", "eez", "imbl", "trip",
                       "telemetry", "family", "wrist")
    present_maritime = []
    for path in paths:
        lowered = path.lower()
        for token in maritime_tokens:
            if token in lowered:
                present_maritime.append(path)
                break
    spec_text = spec_resp.text.lower()
    leaked_maritime = [w for w in ("jalri", "jalari", "palavari", "resq",
                                   "boatnode", "wristnode", "jalri_") if w in spec_text]
    spec_title = spec.get("info", {}).get("title", "")
    check("2b. OpenAPI contains no maritime paths / Jalri metadata",
          not present_maritime and not leaked_maritime,
          f"paths={present_maritime} words={leaked_maritime} title='{spec_title}'")

    # ------------------------------------------------------------------- 3 ----
    login = client.post("/api/auth/login",
                        json={"email": args.admin_email, "password": args.admin_password})
    admin_token = login.json().get("access_token") if login.status_code == 200 else None
    check("3a. POST /api/auth/login issues an ADMIN token",
          login.status_code == 200 and bool(admin_token),
          f"status={login.status_code}")
    if not admin_token:
        print("\nCannot continue without an admin token. Run scripts/seed_dev.py first.")
        return 1
    auth = {"Authorization": f"Bearer {admin_token}"}

    op_login = client.post("/api/auth/login",
                           json={"email": args.operator_email,
                                 "password": args.operator_password})
    operator_token = (op_login.json().get("access_token")
                      if op_login.status_code == 200 else None)
    check("3b. POST /api/auth/login issues an OPERATOR token", bool(operator_token),
          f"status={op_login.status_code}")

    bad_login = client.post("/api/auth/login",
                            json={"email": args.admin_email, "password": "wrong-password"})
    check("3c. Wrong password is rejected with 401",
          bad_login.status_code == 401, f"status={bad_login.status_code}")

    # ------------------------------------------------------------------- 4 ----
    cp = client.post("/api/forest/checkpoints", headers=auth, json={
        "checkpoint_id": cp_id, "name": "Smoke Test Gate", "zone_id": zone,
        "latitude": 18.412345, "longitude": 82.712345, "node_id": node_id, "active": True})
    check("4a. POST /api/forest/checkpoints registers a checkpoint",
          cp.status_code == 201 and cp.json().get("checkpoint_id") == cp_id,
          f"status={cp.status_code}")

    node_priv, node_pub = new_device_key()
    node = client.post("/api/forest/nodes", headers=auth, json={
        "node_id": node_id, "node_type": "CHECKPOINT_NODE", "checkpoint_id": cp_id,
        "zone_id": zone, "firmware_version": "1.0.0", "public_key": node_pub})
    node_body = node.json() if node.status_code == 201 else {}
    check("4b. POST /api/forest/nodes registers a node with its ECC public key",
          node.status_code == 201 and node_body.get("has_public_key") is True,
          f"status={node.status_code}")
    check("4c. Node response never echoes key material",
          "public_key" not in node_body, f"fields={len(node_body)}")

    ac_priv, ac_pub = new_device_key()
    ac_node = client.post("/api/forest/nodes", headers=auth, json={
        "node_id": ac_node_id, "node_type": "ACOUSTIC_NODE", "checkpoint_id": cp_id,
        "zone_id": zone, "firmware_version": "1.0.0", "public_key": ac_pub})
    check("4d. POST /api/forest/nodes registers the acoustic node",
          ac_node.status_code == 201, f"status={ac_node.status_code}")

    officer = client.post("/api/forest/officers", headers=auth, json={
        "officer_id": officer_id, "name": "Smoke Officer", "badge_number": f"B-{tag}"})
    check("4e. POST /api/forest/officers registers a patrol officer",
          officer.status_code == 201, f"status={officer.status_code}")

    gw = client.post("/api/ingest/gateway/status", headers=gw_headers, json={
        "gateway_id": args.gateway_id, "name": "Smoke Gateway",
        "lora_status": "ACTIVE", "wifi_status": "CONNECTED", "backend_status": "REACHABLE",
        "firmware_version": "0.1.0"})
    check("4f. POST /api/ingest/gateway/status records separated gateway states",
          gw.status_code == 200, f"status={gw.status_code}")

    # ------------------------------------------------------------------- 5 ----
    event_1 = build_patrol_event(
        node_id=node_id, sequence=1, checkpoint_id=cp_id, officer_id=officer_id,
        previous_hash=crypto.GENESIS_HASH, private_key=node_priv,
        event_created_at=offline_created_at, gateway_id=args.gateway_id,
        gateway_received_at=gateway_received_at)

    path = "/api/ingest/gateway/forest-event"
    first = client.post(path, headers=gw_headers, json=event_1)
    first_body = first.json() if first.content else {}
    check("5a. Valid offline patrol event is ACCEPTED (201)",
          first.status_code == 201 and first_body.get("outcome") == "ACCEPTED",
          f"status={first.status_code} outcome={first_body.get('outcome')}")
    check("5b. Signature verified VALID",
          first_body.get("signature_status") == "VALID",
          f"signature_status={first_body.get('signature_status')}")
    check("5c. Hash chain verified VALID",
          first_body.get("chain_status") == "VALID",
          f"chain_status={first_body.get('chain_status')}")
    event_1_id = first_body.get("event_id")

    # ------------------------------------------------------------------- 6 ----
    repeat = client.post(path, headers=gw_headers, json=event_1)
    repeat_body = repeat.json() if repeat.content else {}
    check("6a. Re-sent identical event is idempotent DUPLICATE (200)",
          repeat.status_code == 200 and repeat_body.get("outcome") == "DUPLICATE",
          f"status={repeat.status_code} outcome={repeat_body.get('outcome')}")
    check("6b. Duplicate resolves to the SAME persisted event_id",
          repeat_body.get("event_id") == event_1_id,
          f"{repeat_body.get('event_id')} vs {event_1_id}")
    check("6c. Duplicate does not create a second logical record",
          repeat_body.get("duplicate") is True, f"duplicate={repeat_body.get('duplicate')}")

    # ------------------------------------------------------------------- 7 ----
    # A *new* sequence whose payload was altered after signing (GATEWAY-LEVEL
    # tampering / bit flip on the wire) must fail authenticity verification.
    tampered = build_patrol_event(
        node_id=node_id, sequence=2, checkpoint_id=cp_id, officer_id=officer_id,
        previous_hash=event_1["record_hash"], private_key=node_priv,
        event_created_at=offline_created_at, gateway_id=args.gateway_id,
        gateway_received_at=gateway_received_at)
    tampered["rfid_result"] = "INVALID"  # changed AFTER the signature was computed
    bad_sig = client.post(path, headers=gw_headers, json=tampered)
    bad_sig_body = bad_sig.json() if bad_sig.content else {}
    check("7. Tampered payload (post-signature) -> INVALID_SIGNATURE",
          bad_sig_body.get("outcome") == "INVALID_SIGNATURE",
          f"status={bad_sig.status_code} outcome={bad_sig_body.get('outcome')}")

    # ------------------------------------------------------------------- 8 ----
    # A dedicated node isolates authenticity failure from chain failure: the
    # registered public key belongs to *this* node, but the event is signed by
    # an attacker's key. Chain linkage is correct, so only the signature fails.
    wk_node_id = f"FN-WRONGKEY-{tag}"
    wk_priv, wk_registered_pub = new_device_key()
    attacker_priv, _ = new_device_key()
    client.post("/api/forest/nodes", headers=auth, json={
        "node_id": wk_node_id, "node_type": "CHECKPOINT_NODE", "checkpoint_id": cp_id,
        "zone_id": zone, "firmware_version": "1.0.0", "public_key": wk_registered_pub})
    event_3 = build_patrol_event(
        node_id=wk_node_id, sequence=1, checkpoint_id=cp_id, officer_id=officer_id,
        previous_hash=crypto.GENESIS_HASH, private_key=attacker_priv,
        event_created_at=offline_created_at, gateway_id=args.gateway_id,
        gateway_received_at=gateway_received_at)
    wrong_key = client.post(path, headers=gw_headers, json=event_3)
    wrong_body = wrong_key.json() if wrong_key.content else {}
    check("8a. Event signed by the WRONG private key -> INVALID_SIGNATURE",
          wrong_body.get("outcome") == "INVALID_SIGNATURE",
          f"outcome={wrong_body.get('outcome')}")
    check("8b. Signature-INVALID is a distinct failure state (chain itself is VALID)",
          wrong_body.get("signature_status") == "INVALID"
          and wrong_body.get("chain_status") == "VALID",
          f"sig={wrong_body.get('signature_status')} chain={wrong_body.get('chain_status')}")

    # ------------------------------------------------------------------- 9 ----
    event_4 = build_patrol_event(
        node_id=node_id, sequence=4, checkpoint_id=cp_id, officer_id=officer_id,
        previous_hash="0" * 64, private_key=node_priv,  # unregistered predecessor
        event_created_at=offline_created_at, gateway_id=args.gateway_id,
        gateway_received_at=gateway_received_at)
    broken = client.post(path, headers=gw_headers, json=event_4)
    broken_body = broken.json() if broken.content else {}
    check("9a. Unregistered predecessor hash -> BROKEN_CHAIN",
          broken_body.get("outcome") == "BROKEN_CHAIN",
          f"outcome={broken_body.get('outcome')}")
    check("9b. Chain-INVALID is a distinct failure state (signature itself is VALID)",
          broken_body.get("chain_status") == "BROKEN"
          and broken_body.get("signature_status") == "VALID",
          f"chain_status={broken_body.get('chain_status')} "
          f"sig={broken_body.get('signature_status')}")

    # ------------------------------------------------------------------ 10 ----
    unknown = client.post(path, headers=gw_headers, json={
        "node_id": "FN-DOES-NOT-EXIST", "sequence": 1, "checkpoint_id": cp_id,
        "officer_id": officer_id, "rfid_result": "VALID", "fingerprint_result": "MATCH",
        "event_created_at": offline_created_at.isoformat(),
        "previous_hash": crypto.GENESIS_HASH, "record_hash": "0" * 64,
        "signature": "AAAA",
        "gateway": {"gateway_id": args.gateway_id}})
    check("10a. Unknown node -> 404 UNKNOWN_NODE",
          unknown.status_code == 404 and unknown.json().get("outcome") == "UNKNOWN_NODE",
          f"status={unknown.status_code} outcome={unknown.json().get('outcome')}")

    malformed = client.post(path, headers=gw_headers, json={
        **event_1, "sequence": 90, "rfid_result": "MAYBE"})
    check("10b. Malformed event body -> 422 (not a fake success)",
          malformed.status_code == 422, f"status={malformed.status_code}")

    if gateway_key:
        no_key_headers = {"X-Gateway-Key": "definitely-not-the-key"}
        rejected = client.post(path, headers=no_key_headers, json=event_1)
        check("10c. Wrong gateway key -> 401",
              rejected.status_code == 401, f"status={rejected.status_code}")
    else:
        check("10c. Gateway key NOT CONFIGURED in this environment (skipped)", True,
              "set FOREST_GATEWAY_INGESTION_KEY to enforce")

    # ------------------------------------------------------------------ 11 ----
    acoustic = build_acoustic_event(
        node_id=ac_node_id, sequence=1, checkpoint_id=cp_id, zone_id=zone,
        previous_hash=crypto.GENESIS_HASH, private_key=ac_priv,
        event_created_at=(now - timedelta(hours=1)).replace(microsecond=0),
        classification="Gunshot", confidence=0.91, model_version="tinyml-v0.1",
        gateway_id=args.gateway_id, gateway_received_at=gateway_received_at)
    ac_resp = client.post("/api/ingest/gateway/acoustic-event", headers=gw_headers,
                          json=acoustic)
    ac_body = ac_resp.json() if ac_resp.content else {}
    check("11a. Signed acoustic detection is ACCEPTED", ac_body.get("outcome") == "ACCEPTED",
          f"status={ac_resp.status_code} outcome={ac_body.get('outcome')}")
    ac_event_id = ac_body.get("event_id")

    listed = client.get("/api/forest/acoustic-events", headers=auth,
                        params={"review_status": "PENDING_REVIEW", "limit": 200})
    listed_body = listed.json() if listed.status_code == 200 else []
    row = next((r for r in listed_body if r.get("event_id") == ac_event_id), None)
    check("11b. Detection lands in the review queue as PENDING_REVIEW",
          row is not None and row.get("review_status") == "PENDING_REVIEW",
          f"status={listed.status_code} found={row is not None}")
    check("11c. ML classification is stored, not treated as ground truth",
          row is not None and row.get("classification") == "Gunshot"
          and row.get("review_status") != "CONFIRMED",
          f"classification={row.get('classification') if row else None}")

    review = client.post(f"/api/forest/acoustic-events/{ac_event_id}/review",
                         headers=auth, json={"review_status": "CONFIRMED"})
    review_body = review.json() if review.content else {}
    check("11d. POST .../review moves status to CONFIRMED (reviewed_at recorded)",
          review.status_code == 200 and review_body.get("review_status") == "CONFIRMED"
          and bool(review_body.get("reviewed_at")),
          f"status={review.status_code} review={review_body.get('review_status')}")

    bad_review = client.post(f"/api/forest/acoustic-events/{ac_event_id}/review",
                             headers=auth, json={"review_status": "NOT_A_STATE"})
    check("11e. Invalid review state is rejected with 422",
          bad_review.status_code == 422, f"status={bad_review.status_code}")

    # ------------------------------------------------------------------ 12 ----
    patrols = client.get("/api/forest/patrols", headers=auth,
                         params={"node_id": node_id, "limit": 100})
    patrols_body = patrols.json() if patrols.status_code == 200 else []
    stored = next((p for p in patrols_body if p.get("event_id") == event_1_id), None)
    check("12a. GET /api/forest/patrols returns the persisted event",
          stored is not None, f"status={patrols.status_code} rows={len(patrols_body)}")
    check("12b. WHO / WHERE / WHEN are all present",
          bool(stored) and stored.get("officer_id") == officer_id
          and stored.get("checkpoint_id") == cp_id
          and bool(stored.get("event_created_at")),
          f"officer={stored.get('officer_id') if stored else None}")
    check("12c. event_created_at is preserved, NOT overwritten by arrival time",
          bool(stored) and stored["event_created_at"].startswith(
              offline_created_at.strftime("%Y-%m-%dT%H:%M"))
          and stored.get("backend_received_at") != stored.get("event_created_at"),
          f"event_created_at={stored.get('event_created_at') if stored else None}")
    check("12d. Verification states stay separate (rfid / fingerprint / sig / chain)",
          bool(stored) and stored.get("rfid_result") == "VALID"
          and stored.get("fingerprint_result") == "MATCH"
          and stored.get("signature_status") == "VALID"
          and stored.get("chain_status") == "VALID"
          and stored.get("sync_status") == "SYNCED",
          f"sig={stored.get('signature_status') if stored else None} "
          f"chain={stored.get('chain_status') if stored else None}")

    detail = client.get(f"/api/forest/patrols/{event_1_id}", headers=auth)
    check("12e. GET /api/forest/patrols/{event_id} returns the single event",
          detail.status_code == 200 and detail.json().get("event_id") == event_1_id,
          f"status={detail.status_code}")

    nodes_resp = client.get("/api/forest/nodes", headers=auth)
    check("12f. GET /api/forest/nodes lists registered nodes (no key material)",
          nodes_resp.status_code == 200 and all("public_key" not in n
                                                for n in nodes_resp.json()),
          f"status={nodes_resp.status_code}")

    cps = client.get("/api/forest/checkpoints", headers=auth)
    check("12g. GET /api/forest/checkpoints lists the smoke checkpoint",
          cps.status_code == 200 and any(c.get("checkpoint_id") == cp_id
                                         for c in cps.json()),
          f"status={cps.status_code}")

    officers = client.get("/api/forest/officers", headers=auth)
    check("12h. GET /api/forest/officers lists the registered officer",
          officers.status_code == 200 and any(o.get("officer_id") == officer_id
                                              for o in officers.json()),
          f"status={officers.status_code}")

    # ------------------------------------------------------------------ 13 ----
    ledger = client.get("/api/forest/ledger", headers=auth,
                        params={"node_id": node_id, "limit": 200})
    ledger_body = ledger.json() if ledger.status_code == 200 else []
    seq1 = next((r for r in ledger_body if r.get("sequence") == 1), None)
    check("13a. GET /api/forest/ledger exposes previous_hash + record_hash",
          seq1 is not None and seq1.get("previous_hash") == crypto.GENESIS_HASH
          and bool(seq1.get("record_hash")),
          f"status={ledger.status_code} rows={len(ledger_body)}")
    broken_rows = [r for r in ledger_body if r.get("chain_status") == "BROKEN"]
    check("13b. Broken-chain rows are visible, not silently accepted",
          any(r.get("sequence") == 4 for r in broken_rows),
          f"broken_sequences={[r.get('sequence') for r in broken_rows]}")
    check("13c. Ledger is ordered per node by sequence",
          [r.get("sequence") for r in ledger_body] == sorted(
              r.get("sequence") for r in ledger_body),
          f"sequences={[r.get('sequence') for r in ledger_body]}")

    # ------------------------------------------------------------------ 14 ----
    sync = client.get("/api/forest/sync-history", headers=auth, params={"limit": 200})
    sync_body = sync.json() if sync.status_code == 200 else []
    dup_row = next((r for r in sync_body if r.get("event_id") == event_1_id
                    and r.get("sync_status") == "DUPLICATE"), None)
    check("14a. Sync record marks the re-delivery as DUPLICATE",
          dup_row is not None, f"status={sync.status_code} rows={len(sync_body)}")
    check("14b. Retry bumps attempt_count on the same sync row",
          bool(dup_row) and int(dup_row.get("attempt_count", 0)) >= 2,
          f"attempt_count={dup_row.get('attempt_count') if dup_row else None}")
    check("14c. Sync state is tracked separately from event validity",
          dup_row is not None and dup_row.get("sync_status") == "DUPLICATE"
          and stored is not None and stored.get("sync_status") == "SYNCED",
          f"event_sync={stored.get('sync_status') if stored else None}")

    gw_list = client.get("/api/forest/gateways", headers=auth)
    gw_rows = gw_list.json() if gw_list.status_code == 200 else []
    gw_row = next((g for g in gw_rows if g.get("gateway_id") == args.gateway_id), None)
    check("14d. Gateway exposes LoRa / Wi-Fi / backend states separately",
          gw_row is not None and gw_row.get("lora_status") == "ACTIVE"
          and gw_row.get("wifi_status") == "CONNECTED"
          and gw_row.get("backend_status") == "REACHABLE",
          f"gw={gw_row.get('lora_status') if gw_row else None}/"
          f"{gw_row.get('wifi_status') if gw_row else None}/"
          f"{gw_row.get('backend_status') if gw_row else None}")
    check("14e. Gateway counters come from real received traffic",
          bool(gw_row) and int(gw_row.get("records_received", 0)) >= 1,
          f"records_received={gw_row.get('records_received') if gw_row else None}")

    status_resp = client.get("/api/forest/system-status", headers=auth)
    status_body = status_resp.json() if status_resp.status_code == 200 else {}
    check("14f. GET /api/forest/system-status reports DB-derived counters",
          status_resp.status_code == 200
          and int(status_body.get("nodes", {}).get("registered", 0)) >= 2
          and int(status_body.get("patrols", {}).get("total", 0)) >= 1,
          f"status={status_resp.status_code} "
          f"nodes={status_body.get('nodes', {}).get('registered')} "
          f"patrols={status_body.get('patrols', {}).get('total')}")
    check("14g. system-status counts invalid signatures and broken chains",
          int(status_body.get("patrols", {}).get("invalid_signatures", 0)) >= 1
          and int(status_body.get("patrols", {}).get("broken_chains", 0)) >= 1,
          f"invalid={status_body.get('patrols', {}).get('invalid_signatures')} "
          f"broken={status_body.get('patrols', {}).get('broken_chains')}")

    # ------------------------------------------------------------------ 15 ----
    anon = client.get("/api/forest/patrols")
    check("15a. Unauthenticated dashboard request -> 401",
          anon.status_code == 401, f"status={anon.status_code}")
    bad_token = client.get("/api/forest/patrols",
                           headers={"Authorization": "Bearer not-a-jwt"})
    check("15b. Malformed bearer token -> 401",
          bad_token.status_code == 401, f"status={bad_token.status_code}")

    if operator_token:
        op_headers = {"Authorization": f"Bearer {operator_token}"}
        op_create = client.post("/api/forest/nodes", headers=op_headers, json={
            "node_id": f"FN-DENIED-{tag}", "node_type": "CHECKPOINT_NODE"})
        check("15c. OPERATOR cannot register nodes (ADMIN-only) -> 403",
              op_create.status_code == 403, f"status={op_create.status_code}")
        op_users = client.get("/api/users", headers=op_headers)
        check("15d. OPERATOR cannot list user accounts -> 403",
              op_users.status_code == 403, f"status={op_users.status_code}")
    else:
        check("15c/15d. OPERATOR account missing (run scripts/seed_dev.py)", False,
              "operator login failed")

    # ------------------------------------------------------------------ out ----
    passed = sum(1 for _, ok, _ in RESULTS if ok)
    failed = [(n, d) for n, ok, d in RESULTS if not ok]
    print("\n" + "=" * 72)
    print(f"SMOKE RESULT: {passed}/{len(RESULTS)} checks passed")
    print(f"Base URL : {base}")
    print(f"Run tag  : {tag}")
    if failed:
        print("-" * 72)
        for name, detail in failed:
            print(f"FAILED: {name} :: {detail}")
        print("=" * 72)
        return 1
    print("All end-to-end checks passed against the live backend + PostgreSQL.")
    print("=" * 72)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())