from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, HttpUrl, field_validator


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)

    @field_validator("password")
    @classmethod
    def password_bytes_limit(cls, v: str) -> str:
        # bcrypt는 72바이트까지만 처리
        if len(v.encode("utf-8")) > 72:
            raise ValueError("password is too long (max 72 bytes)")
        return v


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    created_at: datetime


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class VideoCreate(BaseModel):
    prompt: str = Field(min_length=1, max_length=2000)
    image_url: HttpUrl | None = None
    model: str | None = None
    duration: int | None = Field(default=None, ge=1, le=30)


class VideoJobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    provider: str
    model: str
    prompt: str
    image_url: str | None
    status: str
    video_url: str | None
    error: str | None
    created_at: datetime
    updated_at: datetime
