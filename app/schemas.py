from datetime import datetime

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    HttpUrl,
    field_validator,
    model_validator,
)


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
    """입력에 따라 생성 모드가 자동 결정된다.
    - reference_images 있음 → reference-to-video
    - first_frame_image 있음 → image-to-video
    - 둘 다 없음 → text-to-video
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "prompt": "The character in image 1 walks through the city in image 2 at night",
                "model": "seedance-2.0-mini",
                "reference_images": [
                    "https://example.com/character.png",
                    "https://example.com/city.png",
                ],
                "duration": 5,
            }
        }
    )

    prompt: str = Field(min_length=1, max_length=2000)
    # 모델 패밀리 키 (GET /models 참고). 없으면 기본 모델
    model: str | None = None
    # 참고 이미지: 영상의 첫 장면(선택적으로 마지막 장면)
    first_frame_image: HttpUrl | None = None
    last_frame_image: HttpUrl | None = None
    # 레퍼런스 이미지: 캐릭터/스타일/배경 참고용, 최대 9장. 프롬프트에서 "image 1" 등으로 지칭
    reference_images: list[HttpUrl] = Field(default_factory=list, max_length=9)
    # 영상 길이(초). 없으면 기본값. 길이에 비례해 크레딧 차감
    duration: int | None = Field(default=None, ge=4, le=15)

    @model_validator(mode="after")
    def check_images(self):
        if self.last_frame_image and not self.first_frame_image:
            raise ValueError("last_frame_image requires first_frame_image")
        if self.reference_images and self.first_frame_image:
            raise ValueError("Use either first_frame_image or reference_images, not both")
        return self


class VideoJobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    provider: str
    family: str | None
    mode: str | None
    model: str
    prompt: str
    first_frame_image: str | None
    last_frame_image: str | None
    reference_images: list[str]
    duration: int
    status: str
    video_url: str | None
    error: str | None
    charged: int
    refunded: bool
    created_at: datetime
    updated_at: datetime


class ModelOut(BaseModel):
    key: str
    name: str
    description: str
    price_per_second: int
    price_for_default_duration: int
    default: bool


class UploadOut(BaseModel):
    url: str
    file_name: str
    content_type: str
    size: int


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
