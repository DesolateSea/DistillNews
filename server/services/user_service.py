from service.db.mongo import MongoHandle
from fastapi import HTTPException
from server.security import get_password_hash, verify_password, create_access_token
from server.models.user_model import RegisterModel, LoginModel, SendOTPRequest, VerifyOTPRequest, GoogleLoginRequest
import asyncio
from config import config

_password_slots = asyncio.Semaphore(4)


async def password_work(function, *args):
    await _password_slots.acquire()
    task = asyncio.create_task(asyncio.to_thread(function, *args))

    def finished(job):
        _password_slots.release()
        if not job.cancelled():
            job.exception()
    task.add_done_callback(finished)
    return await asyncio.shield(task)


async def session_for(email):
    user = await MongoHandle.collection("SNAPUsers").find_one({"email": email})
    return create_access_token({"email": email, "version": user.get("session_version", 0)})
try:
    from service.logger import log
except ImportError:
    log = None

CATEGORY = ["World", "Sports", "Technology", "Health", "Business", "Science", "Entertainment"]


async def send_otp(data: SendOTPRequest):
    from server.services.otp_service import generate_otp, store_otp, send_otp_email

    otp = generate_otp()
    session_token = await store_otp(data.email, otp)
    if not session_token:
        raise HTTPException(status_code=500, detail="Failed to store OTP")

    email_sent = await send_otp_email(data.email, otp)
    if not email_sent:
        from service.db.redis import RedisHandle
        await RedisHandle.client().delete(f"otp_session:{session_token}")
        raise HTTPException(503, "Email delivery unavailable")

    return {
        "session_token": session_token,
        "message": "OTP sent successfully",
    }


async def verify_otp_and_login(data: VerifyOTPRequest):
    from server.services.otp_service import verify_otp
    if not await verify_otp(data.email, data.otp, data.session_token):
        raise HTTPException(status_code=401, detail="Invalid or expired OTP")

    user = await MongoHandle.collection("SNAPUsers").find_one({"email": data.email})
    if not user:
        await MongoHandle.collection("SNAPUsers").insert_one({
            "email": data.email,
            "preferences": [],
            "category_scores": {},
            "bias": {}
        })

    token = await session_for(data.email)
    return {"access_token": token, "token_type": "bearer"}


async def register_user(data: RegisterModel):
    if await MongoHandle.collection("SNAPUsers").find_one({"email": data.email}):
        raise HTTPException(status_code=400, detail="Email already registered")

    hashed_password = await password_work(get_password_hash, data.password)
    await MongoHandle.collection("SNAPUsers").insert_one({
        "email": data.email,
        "password": hashed_password,
        "preferences": []
    })

    token = await session_for(data.email)
    return {"access_token": token, "token_type": "bearer"}


async def login_user(data: LoginModel):
    user = await MongoHandle.collection("SNAPUsers").find_one({"email": data.email})
    if not user or not await password_work(verify_password, data.password, user.get("password")):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = await session_for(data.email)
    return {"access_token": token, "token_type": "bearer"}


async def update_user_preferences(data, current_user):
    category_scores = {}
    bias = {}
    for cat in CATEGORY:
        if cat in data.preferences:
            category_scores[cat] = (0, 0)
            bias[cat] = 1 / len(data.preferences)
        else:
            category_scores[cat] = (0, 0.0)
            bias[cat] = 0
    await MongoHandle.collection("SNAPUsers").update_one(
        {"email": current_user["email"]},
        {"$set": {"category_scores": category_scores, "preferences": data.preferences, "bias": bias}},
    )
    try:
        from service.db import RedisHandle
        r = RedisHandle.client()
        if r:
            await r.delete(f"recommendation:user:{current_user['email']}")
            await r.delete("cache:feed:default")
    except Exception:
        pass
    return {"message": "Preferences updated"}


async def google_login_user(data: GoogleLoginRequest):
    import httpx
    if not config.GOOGLE_CLIENT_ID:
        raise HTTPException(503, "Google login is not configured")
    token = data.id_token or data.access_token
    if not token:
        raise HTTPException(401, "A verified Google token is required")
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get("https://oauth2.googleapis.com/tokeninfo",
                                    params={"id_token" if data.id_token else "access_token": token})
            if resp.status_code != 200:
                raise HTTPException(401, "Invalid Google token")
            claims = resp.json()
            if claims.get("aud") != config.GOOGLE_CLIENT_ID or int(claims.get("expires_in", 0)) <= 0:
                raise HTTPException(401, "Invalid Google token audience or expiry")
            if data.access_token and not data.id_token:
                resp = await client.get("https://www.googleapis.com/oauth2/v3/userinfo",
                                        headers={"Authorization": f"Bearer {token}"})
                if resp.status_code != 200:
                    raise HTTPException(401, "Invalid Google token")
                claims = resp.json()
            if claims.get("email_verified") not in (True, "true") or not claims.get("email"):
                raise HTTPException(401, "Google email is not verified")
            user_email = str(claims["email"])
    except (httpx.HTTPError, ValueError, TypeError, KeyError):
        raise HTTPException(401, "Could not verify Google account")

    user = await MongoHandle.collection("SNAPUsers").find_one({"email": user_email})
    if not user:
        await MongoHandle.collection("SNAPUsers").insert_one({
            "email": user_email,
            "preferences": [],
            "category_scores": {},
            "bias": {},
            "auth_provider": "google"
        })

    token = await session_for(user_email)
    return {"access_token": token, "token_type": "bearer"}
