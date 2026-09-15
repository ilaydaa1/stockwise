from pydantic import BaseModel, EmailStr, field_validator


class RegisterRequest(BaseModel):
    name: str
    email: EmailStr
    password: str
    password_confirm: str

    @field_validator("name")
    @classmethod
    def name_must_not_be_blank(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 1:
            raise ValueError("İsim boş olamaz")
        if len(v) > 255:
            raise ValueError("İsim çok uzun")
        return v

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v: str) -> str:
        if len(v) < 12:
            raise ValueError("Şifre en az 12 karakter olmalıdır")
        return v

    @field_validator("password_confirm")
    @classmethod
    def passwords_must_match(cls, v: str, info) -> str:
        if "password" in info.data and v != info.data["password"]:
            raise ValueError("Şifreler eşleşmiyor")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: str
    email: str
    name: str
    created_at: str


class MessageResponse(BaseModel):
    message: str
