import json
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    # 보유 크레딧 (1크레딧 = 1원)
    credits: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    jobs: Mapped[list["VideoJob"]] = relationship(back_populates="user")


class VideoJob(Base):
    __tablename__ = "video_jobs"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    provider: Mapped[str] = mapped_column(String(50))
    # 제공자 실제 모델 ID (예: bytedance/seedance-2.0/image-to-video)
    model: Mapped[str] = mapped_column(String(255))
    prompt: Mapped[str] = mapped_column(Text)
    # 참고 이미지(첫 장면) URL
    image_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    duration: Mapped[int] = mapped_column(Integer, default=5)
    external_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # pending | processing | completed | failed
    status: Mapped[str] = mapped_column(String(32), default="pending")
    video_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    # 차감된 크레딧 (어드민은 0), 실패 시 환불 여부
    charged: Mapped[int] = mapped_column(Integer, default=0)
    refunded: Mapped[bool] = mapped_column(Boolean, default=False)
    # 모델 패밀리(예: seedance-2.0-mini), 생성 모드(text|image|reference)
    family: Mapped[str | None] = mapped_column(String(64), nullable=True)
    mode: Mapped[str | None] = mapped_column(String(16), nullable=True)
    # 참고 이미지(마지막 장면) URL, 레퍼런스 이미지 URL 목록(JSON)
    last_frame_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    reference_images_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    user: Mapped[User] = relationship(back_populates="jobs")

    @property
    def first_frame_image(self) -> str | None:
        return self.image_url

    @property
    def last_frame_image(self) -> str | None:
        return self.last_frame_url

    @property
    def reference_images(self) -> list[str]:
        if not self.reference_images_json:
            return []
        try:
            return list(json.loads(self.reference_images_json))
        except ValueError:
            return []


class CreditTransaction(Base):
    """크레딧 원장: 충전(+), 사용(-), 환불(+) 기록"""

    __tablename__ = "credit_transactions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    amount: Mapped[int] = mapped_column(Integer)
    reason: Mapped[str] = mapped_column(String(32))  # topup | video | refund
    ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class PaymentOrder(Base):
    __tablename__ = "payment_orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    package_id: Mapped[str] = mapped_column(String(32))
    amount: Mapped[int] = mapped_column(Integer)  # 결제 금액(원)
    credits: Mapped[int] = mapped_column(Integer)  # 지급 크레딧
    # pending | paid | failed
    status: Mapped[str] = mapped_column(String(16), default="pending")
    payment_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    fail_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
