from service.db.mongo import MongoHandle
from fastapi import HTTPException
from server.security import get_password_hash, verify_password, create_access_token
from server.models.user_model import RegisterModel, LoginModel, SendOTPRequest, VerifyOTPRequest
from utils.logger import log

CATEGORY = ["World", "Sports", "Technology", "Health", "Business", "Science", "Entertainment"]


async def send_otp(data: SendOTPRequest):
    from server.services.otp_service import generate_otp, store_otp, send_otp_email

    otp = generate_otp()
    session_token = await store_otp(data.email, otp)
    if not session_token:
        raise HTTPException(status_code=500, detail="Failed to store OTP")

    log.info(f"OTP Code for {data.email} → {otp} (session: {session_token[:8]}…)")

    email_sent = await send_otp_email(data.email, otp)
    if not email_sent:
        log.warn(f"Email delivery failed. OTP={otp} session={session_token[:8]}… stored in Redis.")

    return {
        "session_token": session_token,
        "message": "OTP sent successfully" if email_sent else "OTP generated (email delivery failed, check server logs)",
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

    token = create_access_token({"email": data.email})
    return {"access_token": token, "token_type": "bearer"}


async def register_user(data: RegisterModel):
    if await MongoHandle.collection("SNAPUsers").find_one({"email": data.email}):
        raise HTTPException(status_code=400, detail="Email already registered")

    hashed_password = get_password_hash(data.password)
    await MongoHandle.collection("SNAPUsers").insert_one({
        "email": data.email,
        "password": hashed_password,
        "preferences": []
    })

    token = create_access_token({"email": data.email})
    return {"access_token": token, "token_type": "bearer"}


async def login_user(data: LoginModel):
    user = await MongoHandle.collection("SNAPUsers").find_one({"email": data.email})
    if not user or not verify_password(data.password, user["password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token({"email": data.email})
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
    return {"message": "Preferences updated"}