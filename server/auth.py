import os
import secrets

import jwt
from fastapi import Depends, HTTPException, Request
from service.db.mongo import MongoHandle
from server.security import decode_session


def allowed_origins():
    return [origin.strip() for origin in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",") if origin.strip()]


def check_origin(request: Request):
    if request.headers.get("origin") not in allowed_origins():
        raise HTTPException(403, "Untrusted request origin")


async def get_optional_user(request: Request):
    token = request.cookies.get("SNAPsession")
    if not token:
        return None
    try:
        payload = decode_session(token)
        user = await MongoHandle.collection("SNAPUsers").find_one({"email": payload["sub"]})
        if not user or payload["version"] != user.get("session_version", 0):
            raise HTTPException(401, "Session expired")
        if request.method not in {"GET", "HEAD", "OPTIONS"}:
            check_origin(request)
            if not secrets.compare_digest(request.headers.get("x-csrf-token", ""), payload["csrf"]):
                raise HTTPException(403, "Invalid CSRF token")
        return user
    except (jwt.InvalidTokenError, ValueError, TypeError, KeyError):
        raise HTTPException(401, "Invalid session")


async def get_current_user(user=Depends(get_optional_user)):
    if user is None:
        raise HTTPException(401, "Authentication required")
    return user
