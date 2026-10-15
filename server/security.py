"""Password compatibility and short-lived, revocable browser sessions."""
import os
import secrets
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from config import config

ALGORITHM = "HS256"


def jwt_secret():
    secret = config.JWT_SECRET
    if not secret or len(secret.encode()) < 32:
        raise RuntimeError("JWT_SECRET must contain at least 32 bytes")
    return secret


def get_password_hash(password: str):
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, hashed_password: str):
    # Passlib truncated existing passwords; permit that only for legacy login.
    try:
        return bcrypt.checkpw(password.encode()[:72], hashed_password.encode())
    except (ValueError, TypeError, AttributeError):
        return False


def create_access_token(data: dict):
    now = datetime.now(timezone.utc)
    return jwt.encode({**data, "sub": data["email"], "iat": now,
                      "exp": now + timedelta(minutes=int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))),
                      "version": data.get("version", 0), "csrf": secrets.token_urlsafe(32),
                      "iss": "distillnews", "aud": "distillnews-browser"},
                     jwt_secret(), algorithm=ALGORITHM)


def decode_session(token):
    return jwt.decode(token, jwt_secret(), algorithms=[ALGORITHM],
                      issuer="distillnews", audience="distillnews-browser",
                      options={"require": ["exp", "iat", "sub", "email", "version", "csrf"]})


def set_session(response, token):
    payload = decode_session(token)
    secure = os.getenv("COOKIE_SECURE", "true").lower() == "true"
    for name, value, httponly in (("SNAPsession", token, True), ("SNAPcsrf", payload["csrf"], False)):
        response.set_cookie(name, value, httponly=httponly, secure=secure,
                            samesite="strict", path="/", max_age=max(0, int(payload["exp"] - datetime.now(timezone.utc).timestamp())))
