from pydantic import BaseModel, Field, EmailStr, field_validator
from typing import Dict, List
CATEGORY = ["World", "Sports", "Technology", "Health", "Business", "Science", "Entertainment"]
class RegisterModel(BaseModel):
    email: EmailStr
    password: str = Field(min_length=12, max_length=72)

    @field_validator("password")
    @classmethod
    def bcrypt_limit(cls, value):
        if len(value.encode()) > 72:
            raise ValueError("Password must be at most 72 UTF-8 bytes")
        return value

class LoginModel(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=1024)

class PreferencesModel(BaseModel):
    preferences: List[str] = Field(max_length=7)

    @field_validator("preferences")
    @classmethod
    def supported_categories(cls, value):
        if len(set(value)) != len(value) or any(cat not in CATEGORY for cat in value):
            raise ValueError("Preferences must be unique supported categories")
        return value
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
    otp: str = Field(pattern=r"^\d{6}$")
    session_token: str = Field(pattern=r"^[a-f0-9]{32}$")

class GoogleLoginRequest(BaseModel):
    id_token: str | None = None
    access_token: str | None = None
    email: EmailStr | None = None

if __name__ == "__main__":
    from service.logger import log

    prefs = PreferencesModel(preferences=["travel", "economics"])
    user = UserModel(email="user@example.com", password="securepass", preferences=prefs)
    log.info("UserModel", user.json(indent=2))
