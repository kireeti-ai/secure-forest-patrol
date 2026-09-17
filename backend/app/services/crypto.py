"""Cryptographic verification primitives.

Responsibility separation (do not conflate):

- CRC        -> radio packet corruption (handled in firmware, not here)
- HASH CHAIN -> content + record-history integrity (verify_hash_chain)
- SIGNATURE  -> authenticity / source verification (ECC secp256r1)
- DB constraints -> persistence integrity (UNIQUE / FK in models)

Canonical patrol signing bytes::

    node_id | sequence | event_created_at(iso) | checkpoint_id |
    officer_id | rfid_result | fingerprint_result | previous_hash | record_hash

Canonical acoustic signing bytes::

    node_id | sequence | event_created_at(iso) | checkpoint_id |
    zone_id | classification | confidence | model_version |
    previous_hash | record_hash

Record hash (SHA-256 hex)::

    SHA256(node_id | sequence | event_created_at(iso) | payload_digest | previous_hash)

Signatures are DER-encoded ECDSA (secp256r1 / SHA-256), transported
base64-encoded. Verification uses the ``cryptography`` package — no
hand-rolled crypto.
"""

from __future__ import annotations

import base64
import hashlib
from datetime import datetime

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec


CURVE = ec.SECP256R1()
GENESIS_HASH = "GENESIS"


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def compute_record_hash(
    *,
    node_id: str,
    sequence: int,
    event_created_at: datetime,
    payload_digest: str,
    previous_hash: str,
) -> str:
    canonical = "|".join(
        [node_id, str(sequence), event_created_at.isoformat(), payload_digest, previous_hash or GENESIS_HASH]
    )
    return sha256_hex(canonical.encode("utf-8"))


def patrol_payload_digest(
    *,
    checkpoint_id: str | None,
    officer_id: str | None,
    rfid_result: str | None,
    fingerprint_result: str | None,
) -> str:
    canonical = "|".join([checkpoint_id or "", officer_id or "", rfid_result or "", fingerprint_result or ""])
    return sha256_hex(canonical.encode("utf-8"))


def acoustic_payload_digest(
    *,
    classification: str,
    confidence: float,
    model_version: str | None,
) -> str:
    canonical = "|".join([classification, repr(float(confidence)), model_version or ""])
    return sha256_hex(canonical.encode("utf-8"))


def patrol_signing_bytes(
    *,
    node_id: str,
    sequence: int,
    event_created_at: datetime,
    checkpoint_id: str | None,
    officer_id: str | None,
    rfid_result: str | None,
    fingerprint_result: str | None,
    previous_hash: str,
    record_hash: str,
) -> bytes:
    return "|".join(
        [
            node_id,
            str(sequence),
            event_created_at.isoformat(),
            checkpoint_id or "",
            officer_id or "",
            rfid_result or "",
            fingerprint_result or "",
            previous_hash or GENESIS_HASH,
            record_hash,
        ]
    ).encode("utf-8")


def acoustic_signing_bytes(
    *,
    node_id: str,
    sequence: int,
    event_created_at: datetime,
    checkpoint_id: str | None,
    zone_id: str | None,
    classification: str,
    confidence: float,
    model_version: str | None,
    previous_hash: str,
    record_hash: str,
) -> bytes:
    return "|".join(
        [
            node_id,
            str(sequence),
            event_created_at.isoformat(),
            checkpoint_id or "",
            zone_id or "",
            classification,
            repr(float(confidence)),
            model_version or "",
            previous_hash or GENESIS_HASH,
            record_hash,
        ]
    ).encode("utf-8")


def load_public_key(public_key_pem_or_hex: str) -> ec.EllipticCurvePublicKey:
    """Accept PEM (SEC1/SubjectPublicKeyInfo) or raw uncompressed hex (04||X||Y)."""
    text = (public_key_pem_or_hex or "").strip()
    if not text:
        raise ValueError("empty public key")
    if "BEGIN" in text:
        key = serialization.load_pem_public_key(text.encode("utf-8"))
    else:
        raw = bytes.fromhex(text)
        if len(raw) == 64:  # X||Y without prefix
            raw = b"\x04" + raw
        key = ec.EllipticCurvePublicKey.from_encoded_point(CURVE, raw)
    if not isinstance(key, ec.EllipticCurvePublicKey):
        raise ValueError("not an EC public key")
    return key


def verify_signature(*, public_key: str, message: bytes, signature_b64: str) -> bool:
    """Return True iff the DER/base64 ECDSA signature is valid. Never raises."""
    try:
        key = load_public_key(public_key)
        signature = base64.b64decode(signature_b64)
        key.verify(signature, message, ec.ECDSA(hashes.SHA256()))
        return True
    except (ValueError, InvalidSignature, Exception):
        return False


def verify_hash_chain(*, previous_hash: str | None, expected_previous: str | None) -> bool:
    """Genesis records use previous_hash GENESIS (or empty for the first record)."""
    if expected_previous is None:
        return (previous_hash or GENESIS_HASH) in ("", GENESIS_HASH)
    return (previous_hash or "") == expected_previous
