from pydantic import BaseModel, Field, EmailStr
from typing import Dict, List
CATEGORY = ["World", "Sports", "Technology", "Health", "Business", "Science", "Entertainment"]
class RegisterModel(BaseModel):
    email: EmailStr
    password: str

class LoginModel(BaseModel):
    email: EmailStr
    password: str

class PreferencesModel(BaseModel):
    preferences: List[str]
    category_scores: Dict[str, tuple] = Field(
        default_factory=lambda: {cat: (0, 0.0) for cat in CATEGORY}
    )
    bias: Dict[str, float] = Field(default_factory=lambda: {cat: 1/len(CATEGORY) for cat in CATEGORY})

class UserModel(RegisterModel):
    preferences: PreferencesModel

class SendOTPRequest(BaseModel):
    email: EmailStr

class VerifyOTPRequest(BaseModel):
    email: EmailStr
    otp: str
    session_token: str

class GoogleLoginRequest(BaseModel):
    id_token: str | None = None
    access_token: str | None = None
    email: EmailStr | None = None

if __name__ == "__main__":
    from service.logger import log

    prefs = PreferencesModel(preferences=["travel", "economics"])
    user = UserModel(email="user@example.com", password="securepass", preferences=prefs)
    log.info("UserModel", user.json(indent=2))
