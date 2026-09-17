"""Shared signed-event fixtures (deterministic vectors, secp256r1)."""

from __future__ import annotations

import base64
from datetime import datetime, timezone

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec

from app.services import crypto

# Fixed private key (hex) so vectors are deterministic across runs.
PRIVATE_HEX = "c9" * 32


def private_key():
    return ec.derive_private_key(int.from_bytes(bytes.fromhex(PRIVATE_HEX), "big"), ec.SECP256R1())


def public_pem() -> str:
    return private_key().public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo).decode()


def wrong_public_pem() -> str:
    other = ec.derive_private_key(0xDEADBEEF, ec.SECP256R1())
    return other.public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo).decode()


def sign(message: bytes) -> str:
    der = private_key().sign(message, ec.ECDSA(hashes.SHA256()))
    return base64.b64encode(der).decode()


def patrol_payload(node_id="FN-001", sequence=1, checkpoint_id="CP-001",
                   officer_id="OFF-001", created=None, previous_hash="GENESIS"):
    created = created or datetime(2026, 9, 17, 9, 15, 3, tzinfo=timezone.utc)
    digest = crypto.patrol_payload_digest(
        checkpoint_id=checkpoint_id, officer_id=officer_id,
        rfid_result="VALID", fingerprint_result="MATCH")
    record_hash = crypto.compute_record_hash(
        node_id=node_id, sequence=sequence, event_created_at=created,
        payload_digest=digest, previous_hash=previous_hash)
    message = crypto.patrol_signing_bytes(
        node_id=node_id, sequence=sequence, event_created_at=created,
        checkpoint_id=checkpoint_id, officer_id=officer_id,
        rfid_result="VALID", fingerprint_result="MATCH",
        previous_hash=previous_hash, record_hash=record_hash)
    body = {
        "node_id": node_id, "sequence": sequence,
        "checkpoint_id": checkpoint_id, "officer_id": officer_id,
        "rfid_result": "VALID", "fingerprint_result": "MATCH",
        "event_created_at": created.isoformat(),
        "previous_hash": previous_hash, "record_hash": record_hash,
        "signature": sign(message),
        "gateway": {"gateway_id": "GW-01",
                    "received_at": datetime(2026, 9, 17, 13, 27, 11,
                                            tzinfo=timezone.utc).isoformat()},
    }
    return body, created, record_hash


def acoustic_payload(node_id="FN-002", sequence=1, checkpoint_id="CP-002",
                     created=None, previous_hash="GENESIS"):
    created = created or datetime(2026, 9, 17, 10, 0, 0, tzinfo=timezone.utc)
    digest = crypto.acoustic_payload_digest(
        classification="Chainsaw", confidence=0.91, model_version="v1")
    record_hash = crypto.compute_record_hash(
        node_id=node_id, sequence=sequence, event_created_at=created,
        payload_digest=digest, previous_hash=previous_hash)
    message = crypto.acoustic_signing_bytes(
        node_id=node_id, sequence=sequence, event_created_at=created,
        checkpoint_id=checkpoint_id, zone_id="ZONE-B",
        classification="Chainsaw", confidence=0.91, model_version="v1",
        previous_hash=previous_hash, record_hash=record_hash)
    body = {
        "node_id": node_id, "sequence": sequence,
        "checkpoint_id": checkpoint_id, "zone_id": "ZONE-B",
        "event_created_at": created.isoformat(),
        "classification": "Chainsaw", "confidence": 0.91, "model_version": "v1",
        "previous_hash": previous_hash, "record_hash": record_hash,
        "signature": sign(message),
        "gateway": {"gateway_id": "GW-01"},
    }
    return body, created, record_hash
