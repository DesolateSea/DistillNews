from fastapi import APIRouter, Depends, Request, Response
from server.models.user_model import RegisterModel, LoginModel, SendOTPRequest, VerifyOTPRequest, GoogleLoginRequest
from server.services.user_service import register_user, login_user, send_otp, verify_otp_and_login, google_login_user
from server.auth import check_origin, get_current_user
from server.security import set_session
from server.limits import limit_key
from service.db.mongo import MongoHandle

router = APIRouter()


async def auth_limit(request: Request, data, action):
    check_origin(request)
    peer = request.client.host if request.client else "unknown"
    await limit_key(peer, f"auth:{action}", 20, 60)
    identity = str(getattr(data, "email", None) or peer).lower()
    await limit_key(identity, f"account:{action}", 5, 60)


def browser_session(response, result):
    set_session(response, result["access_token"])
    return {"authenticated": True}


@router.post("/send-otp")
async def send_otp_endpoint(data: SendOTPRequest, request: Request):
    await auth_limit(request, data, "send-otp")
    return await send_otp(data)


@router.post("/verify-otp")
async def verify_otp_endpoint(data: VerifyOTPRequest, request: Request, response: Response):
    await auth_limit(request, data, "verify-otp")
    return browser_session(response, await verify_otp_and_login(data))


@router.post("/register")
async def register(data: RegisterModel, request: Request, response: Response):
    await auth_limit(request, data, "register")
    return browser_session(response, await register_user(data))


@router.post("/login")
async def login(data: LoginModel, request: Request, response: Response):
    await auth_limit(request, data, "login")
    return browser_session(response, await login_user(data))


@router.post("/google-login")
async def google_login_endpoint(data: GoogleLoginRequest, request: Request, response: Response):
    await auth_limit(request, data, "google")
    return browser_session(response, await google_login_user(data))


@router.get("/session")
async def session(user=Depends(get_current_user)):
    return {"authenticated": True, "email": user["email"]}


@router.post("/logout")
async def logout(response: Response, user=Depends(get_current_user)):
    await MongoHandle.collection("SNAPUsers").update_one(
        {"_id": user["_id"]}, {"$inc": {"session_version": 1}})
    response.delete_cookie("SNAPsession", path="/")
    response.delete_cookie("SNAPcsrf", path="/")
    return {"authenticated": False}
