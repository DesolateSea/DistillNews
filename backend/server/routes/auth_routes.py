from fastapi import APIRouter, HTTPException
from server.models.user_model import RegisterModel, LoginModel, SendOTPRequest, VerifyOTPRequest
from server.services.user_service import register_user, login_user, send_otp, verify_otp_and_login

router = APIRouter()

@router.post("/send-otp")
async def send_otp_endpoint(data: SendOTPRequest):
    return await send_otp(data)

@router.post("/verify-otp")
async def verify_otp_endpoint(data: VerifyOTPRequest):
    return await verify_otp_and_login(data)

@router.post("/register")
async def register(data: RegisterModel):
    return await register_user(data)

@router.post("/login")
async def login(data: LoginModel):
    return await login_user(data)
