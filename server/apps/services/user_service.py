from fastapi import HTTPException
from apps.core.security import get_password_hash, verify_password, create_access_token
from apps.models.user_model import RegisterModel, LoginModel, SendOTPRequest, VerifyOTPRequest
from apps.core.config import DB_URL
from motor.motor_asyncio import AsyncIOMotorClient
from apps.core.config import CATEGORY
client = AsyncIOMotorClient(DB_URL)
users_collection = client.news_db.SNAPUsers

async def send_otp(data: SendOTPRequest):
    from apps.services.otp_service import generate_otp, store_otp, send_otp_email
    import logging
    logger = logging.getLogger("apps.services.user_service")

    otp = generate_otp()
    session_token = await store_otp(data.email, otp)
    if not session_token:
        raise HTTPException(status_code=500, detail="Failed to store OTP")

    # Always log the OTP + session token for development/testing
    logger.info(f"🔑 [OTP LOG] Code for {data.email} → OTP: {otp}  session: {session_token[:8]}…")

    email_sent = await send_otp_email(data.email, otp)
    if not email_sent:
        logger.warning(
            f"⚠️ Email delivery failed. OTP={otp} session={session_token[:8]}… stored in Redis."
        )

    return {
        "session_token": session_token,
        "message": "OTP sent successfully" if email_sent else "OTP generated (email delivery failed, check server logs)",
    }

async def verify_otp_and_login(data: VerifyOTPRequest):
    from apps.services.otp_service import verify_otp
    if not await verify_otp(data.email, data.otp, data.session_token):
        raise HTTPException(status_code=401, detail="Invalid or expired OTP")

    user = await users_collection.find_one({"email": data.email})
    if not user:
        await users_collection.insert_one({
            "email": data.email,
            "preferences": [],
            "category_scores": {},
            "bias": {}
        })

    token = create_access_token({"email": data.email})
    return {"access_token": token, "token_type": "bearer"}

async def register_user(data: RegisterModel):
    if await users_collection.find_one({"email": data.email}):
        raise HTTPException(status_code=400, detail="Email already registered")
    
    hashed_password = get_password_hash(data.password)
    await users_collection.insert_one({
        "email": data.email,
        "password": hashed_password,
        "preferences": []
    })

    token = create_access_token({"email": data.email})
    return {"access_token": token, "token_type": "bearer"}

async def login_user(data: LoginModel):
    user = await users_collection.find_one({"email": data.email})
    if not user or not verify_password(data.password, user["password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    token = create_access_token({"email": data.email})
    return {"access_token": token, "token_type": "bearer"}

async def update_user_preferences(data, current_user):
    category_scores = {}
    bias = {}
    for cat in CATEGORY:
        if cat in data.preferences:
            category_scores[cat] = (0,0) # some initial bias
            bias[cat]=1/len(data.preferences)
        else:
            category_scores[cat] = (0,0.0)
            bias[cat]=0
    await users_collection.update_one({"email": current_user["email"]}, {"$set": {"category_scores": category_scores, "preferences": data.preferences,"bias":bias}})
    return {"message": "Preferences updated"}