"""Password hashing and the (disabled) route guard.

Authentication is disabled by owner decision: the dashboard has no login, so
every route guarded by ``require_roles`` is public.
"""

from __future__ import annotations

import hashlib
import secrets


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 200_000)
    return f"pbkdf2_sha256$200000${salt}${digest.hex()}"


def require_roles(*allowed_roles: str):
    """No-op dependency kept so route signatures stay stable."""

    def dependency() -> None:
        return None

    return dependency
