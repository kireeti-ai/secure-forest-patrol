from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies.database import get_db
from app.core.security import create_access_token, get_current_user, hash_password, require_roles, verify_password
from app.models.user import User

router = APIRouter(prefix="/api", tags=["auth"])


@router.post("/auth/login")
def login(payload: dict, db: Session = Depends(get_db)) -> dict:
    email = str(payload.get("email") or "").strip().lower()
    password = str(payload.get("password") or "")
    if not email or not password:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    user = db.scalar(select(User).where(User.email == email))
    if user is None or not verify_password(password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User is not active")

    token = create_access_token({"sub": str(user.id), "role": user.role}, expires_delta=timedelta(hours=12))
    return {"access_token": token, "token_type": "bearer", "user": {"id": str(user.id), "email": user.email, "role": user.role, "full_name": user.full_name}}


@router.get("/users", response_model=list[dict])
def list_users(db: Session = Depends(get_db), user: User = Depends(require_roles("ADMIN"))) -> list[dict]:
    del user
    rows = db.scalars(select(User).order_by(User.email))
    return [{"id": str(r.id), "email": r.email, "full_name": r.full_name, "role": r.role, "is_active": r.is_active} for r in rows]


@router.get("/me")
def get_me(user: User = Depends(get_current_user)) -> dict:
    return {"id": str(user.id), "email": user.email, "role": user.role, "full_name": user.full_name}
