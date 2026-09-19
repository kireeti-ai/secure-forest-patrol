from __future__ import annotations

import hashlib
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies.database import get_db
from app.models.user import User

security = HTTPBearer(auto_error=False)

_DEFAULT_SECRET = "forest-dev-secret-change-me-before-production-32b"


def get_secret_key() -> str:
    return os.getenv("JWT_SECRET_KEY") or os.getenv("SECRET_KEY") or _DEFAULT_SECRET


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 200_000)
    return f"pbkdf2_sha256$200000${salt}${digest.hex()}"


def verify_password(password: str, password_hash: str) -> bool:
    try:
        scheme, iterations, salt, expected = password_hash.split("$", 3)
        if scheme != "pbkdf2_sha256":
            return False
        actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), int(iterations)).hex()
        return secrets.compare_digest(actual, expected)
    except ValueError:
        # Compatibility for locally seeded records from before per-user salts.
        legacy_salt = os.getenv("PASSWORD_SALT", "forest-patrol")
        actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), legacy_salt.encode("utf-8"), 200_000).hex()
        return secrets.compare_digest(actual, password_hash)


def create_access_token(data: dict[str, Any], expires_delta: timedelta | None = None) -> str:
    to_encode = dict(data)
    expire_at = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=60))
    to_encode["exp"] = expire_at
    return jwt.encode(to_encode, get_secret_key(), algorithm="HS256")


def decode_access_token(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(token, get_secret_key(), algorithms=["HS256"])
    except jwt.PyJWTError as exc:  # pragma: no cover - exercised via HTTP auth path
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authentication credentials") from exc


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None or not credentials.scheme.lower() == "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    payload = decode_access_token(credentials.credentials)
    subject = payload.get("sub")
    if not subject:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")

    user = db.scalar(select(User).where(User.id == subject))
    if user is None:
        user = db.scalar(select(User).where(User.email == subject))
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User is not active")

    return user


def require_roles(*allowed_roles: str):
    def dependency(user: User = Depends(get_current_user)) -> User:
        if not allowed_roles or user.role in allowed_roles:
            return user
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")

    return dependency


def seed_default_users(db: Session) -> None:
    existing = db.scalars(select(User)).all()
    if existing:
        return

    admin = User(
        email="admin@forest.local",
        full_name="System Administrator",
        password_hash=hash_password("ForestAdmin123!"),
        role="ADMIN",
    )
    operator = User(
        email="operator@forest.local",
        full_name="Field Operator",
        password_hash=hash_password("ForestOperator123!"),
        role="OPERATOR",
    )
    db.add_all([admin, operator])
    db.commit()
