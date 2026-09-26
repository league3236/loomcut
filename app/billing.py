from sqlalchemy import update
from sqlalchemy.orm import Session

from app.catalog import ModelFamily
from app.config import get_settings
from app.models import CreditTransaction, User, VideoJob

# 충전 패키지 (1크레딧 = 1원, 큰 패키지일수록 보너스)
PACKAGES: dict[str, dict] = {
    "basic": {"name": "베이직", "amount": 10000, "credits": 10000},
    "standard": {"name": "스탠다드", "amount": 30000, "credits": 31500},
    "pro": {"name": "프로", "amount": 50000, "credits": 55000},
}


def is_admin(user: User) -> bool:
    return user.email.lower() in get_settings().admin_email_set()


def video_cost(family: ModelFamily, duration: int) -> int:
    return family.price_per_second * duration


def try_charge(db: Session, user_id: int, amount: int, reason: str, ref: str | None) -> bool:
    """잔액이 충분할 때만 원자적으로 차감. 커밋은 호출하는 쪽에서."""
    result = db.execute(
        update(User)
        .where(User.id == user_id, User.credits >= amount)
        .values(credits=User.credits - amount)
    )
    if result.rowcount != 1:
        return False
    db.add(CreditTransaction(user_id=user_id, amount=-amount, reason=reason, ref=ref))
    return True


def add_credits(db: Session, user_id: int, amount: int, reason: str, ref: str | None) -> None:
    db.execute(update(User).where(User.id == user_id).values(credits=User.credits + amount))
    db.add(CreditTransaction(user_id=user_id, amount=amount, reason=reason, ref=ref))


def refund_job(db: Session, job: VideoJob) -> None:
    """실패한 작업의 크레딧을 한 번만 환불 (동시 요청에도 중복 환불 방지)"""
    if job.charged <= 0:
        return
    claimed = db.execute(
        update(VideoJob)
        .where(VideoJob.id == job.id, VideoJob.refunded.is_(False))
        .values(refunded=True)
    )
    if claimed.rowcount == 1:
        add_credits(db, job.user_id, job.charged, "refund", f"video:{job.id}")
