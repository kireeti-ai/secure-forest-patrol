#!/usr/bin/env python3
"""Cross-verify a node-produced signature against the REAL backend verification code
(backend/app/services/crypto.py::verify_signature) - the authoritative correctness check for
NodeIdentity/PatrolSigningBytes, not a reimplementation that could independently agree with a bug.

Usage (paste exactly what the node's 'k' serial command printed):
    python3 node-firmware/tools/verify_node_signature.py <pubkey_hex> '<canonical_message>' <signature_b64>

Run from the repo root (needs backend/ importable and the `cryptography` package, already a
backend dependency: `pip install -r backend/requirements.txt` or run inside backend's own venv).
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from app.services import crypto  # noqa: E402


def main() -> int:
    if len(sys.argv) != 4:
        print(__doc__)
        return 2
    pubkey_hex, message, signature_b64 = sys.argv[1], sys.argv[2], sys.argv[3]
    ok = crypto.verify_signature(public_key=pubkey_hex, message=message.encode("utf-8"), signature_b64=signature_b64)
    print(f"pubkey:    {pubkey_hex}")
    print(f"message:   {message}")
    print(f"signature: {signature_b64}")
    print("RESULT:", "VALID - node signature verifies against the real backend crypto.py" if ok else "INVALID")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
