"""Password hashing and session-based authentication helpers."""

from __future__ import annotations

import hashlib
import os

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User

_ITERATIONS = 120_000


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, _ITERATIONS)
    return f"{salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        salt_hex, digest_hex = stored.split("$", 1)
    except ValueError:
        return False
    salt = bytes.fromhex(salt_hex)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, _ITERATIONS)
    return digest.hex() == digest_hex


def login_user(request: Request, user: User) -> None:
    request.session["user_id"] = user.id
    request.session["theme"] = user.theme or "indigo"
    request.session["plan"] = user.plan or "free"


def logout_user(request: Request) -> None:
    request.session.clear()


def get_current_user(
    request: Request, db: Session = Depends(get_db)
) -> User | None:
    user_id = request.session.get("user_id")
    if not user_id:
        return None
    return db.get(User, user_id)


def require_user(user: User | None = Depends(get_current_user)) -> User:
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Login required",
            headers={"Location": "/login"},
        )
    return user


def require_student(user: User = Depends(require_user)) -> User:
    if user.role != "student":
        raise HTTPException(status_code=403, detail="Students only")
    return user


def require_teacher(user: User = Depends(require_user)) -> User:
    if user.role != "teacher":
        raise HTTPException(status_code=403, detail="Teachers only")
    return user
