"""Simple, dependency-free auth.

- Passwords: PBKDF2-SHA256 (stdlib hashlib).
- Tokens: base64(username|role|expiry) signed with HMAC-SHA256.
  Set SECRET_KEY env var in production.
- FastAPI dependencies: require_user (any logged-in role) and
  require_admin. Role enforcement happens HERE in middleware-style
  dependencies, not by route naming, so an operator calling an admin
  URL gets a clean 403.
"""
import base64
import hashlib
import hmac
import os
import time
from fastapi import Depends, HTTPException, Header
from sqlalchemy.orm import Session as DbSession
from .database import get_db
from . import models

SECRET = os.getenv("SECRET_KEY", "change-me-in-production").encode()
TOKEN_TTL_SECONDS = 60 * 60 * 12  # 12 hours


def hash_password(password: str, salt: bytes | None = None) -> str:
    salt = salt or os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 200_000)
    return base64.b64encode(salt).decode() + "$" + base64.b64encode(dk).decode()


def verify_password(password: str, stored: str) -> bool:
    try:
        salt_b64, dk_b64 = stored.split("$")
        salt = base64.b64decode(salt_b64)
        expected = base64.b64decode(dk_b64)
        dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 200_000)
        return hmac.compare_digest(dk, expected)
    except Exception:
        return False


def make_token(username: str, role: str) -> str:
    exp = int(time.time()) + TOKEN_TTL_SECONDS
    payload = f"{username}|{role}|{exp}".encode()
    sig = hmac.new(SECRET, payload, hashlib.sha256).digest()
    return base64.urlsafe_b64encode(payload).decode() + "." + \
        base64.urlsafe_b64encode(sig).decode()


def parse_token(token: str) -> dict | None:
    try:
        payload_b64, sig_b64 = token.split(".")
        payload = base64.urlsafe_b64decode(payload_b64)
        sig = base64.urlsafe_b64decode(sig_b64)
        expected = hmac.new(SECRET, payload, hashlib.sha256).digest()
        if not hmac.compare_digest(sig, expected):
            return None
        username, role, exp = payload.decode().split("|")
        if int(exp) < time.time():
            return None
        return {"username": username, "role": role}
    except Exception:
        return None


def require_user(authorization: str = Header(default=""),
                 db: DbSession = Depends(get_db)) -> dict:
    if not authorization.startswith("Bearer "):
        raise HTTPException(401, "Missing token")
    info = parse_token(authorization.removeprefix("Bearer ").strip())
    if not info:
        raise HTTPException(401, "Invalid or expired token, log in again")
    user = db.query(models.User).filter_by(username=info["username"]).first()
    if not user:
        raise HTTPException(401, "Unknown user")
    return {"username": user.username, "role": user.role}


def require_admin(user: dict = Depends(require_user)) -> dict:
    if user["role"] != "ADMIN":
        raise HTTPException(403, "Admin access required")
    return user
