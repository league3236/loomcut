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
    id: int
    email: EmailStr
    credits: int
    is_admin: bool
    created_at: datetime


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class VideoCreate(BaseModel):
    prompt: str = Field(min_length=1, max_length=2000)
    image_url: HttpUrl | None = None
    model: str | None = None
    # 영상 길이(초). 없으면 기본값 사용. 길이에 비례해 크레딧 차감
    duration: int | None = Field(default=None, ge=4, le=15)


class VideoJobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    provider: str
    model: str
    prompt: str
    image_url: str | None
    duration: int
    status: str
    video_url: str | None
    error: str | None
    charged: int
    refunded: bool
    created_at: datetime
    updated_at: datetime


class PackageOut(BaseModel):
    id: str
    name: str
    amount: int
    credits: int


class PaymentConfigOut(BaseModel):
    client_key: str
    price_per_second: int
    default_duration: int
    packages: list[PackageOut]


class OrderCreate(BaseModel):
    package_id: str


class OrderOut(BaseModel):
    order_id: str
    order_name: str
    amount: int
    credits: int
    customer_email: str


class PaymentConfirm(BaseModel):
    payment_key: str
    order_id: str
    amount: int


class PaymentResult(BaseModel):
    order_id: str
    status: str
    credits_added: int
    balance: int


class CreditTransactionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    amount: int
    reason: str
    ref: str | None
    created_at: datetime
