from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.billing import is_admin, refund_job, try_charge, video_cost
from app.config import get_settings
from app.database import get_db
from app.models import User, VideoJob
from app.providers import ProviderError, get_provider
from app.schemas import VideoCreate, VideoJobOut
from app.security import get_current_user

router = APIRouter(prefix="/videos", tags=["videos"])

ACTIVE_STATUSES = {"pending", "processing"}


@router.post("", response_model=VideoJobOut, status_code=status.HTTP_202_ACCEPTED)
async def create_video(
    body: VideoCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    s = get_settings()
    image_url = str(body.image_url) if body.image_url else None
    model = body.model or (s.default_i2v_model if image_url else s.default_t2v_model)
    duration = body.duration or s.default_duration
    cost = 0 if is_admin(user) else video_cost(duration)
    provider = get_provider()

    job = VideoJob(
        user_id=user.id,
        provider=provider.name,
        model=model,
        prompt=body.prompt,
        image_url=image_url,
        duration=duration,
        charged=cost,
    )
    db.add(job)
    db.flush()

    # 생성 전에 크레딧 선차감 (어드민은 무료)
    if cost > 0 and not try_charge(db, user.id, cost, "video", f"video:{job.id}"):
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail={
                "message": "Insufficient credits",
                "required": cost,
                "balance": user.credits,
            },
        )
    db.commit()
    db.refresh(job)

    try:
        result = await provider.submit(
            model=model, prompt=body.prompt, image_url=image_url, duration=duration
        )
    except Exception as e:  # noqa: BLE001
        job.status = "failed"
        job.error = str(e)
        refund_job(db, job)
        db.commit()
        raise HTTPException(status_code=502, detail=f"Video provider error: {e}")

    job.external_id = result.external_id
    job.status = result.status
    job.video_url = result.video_url
    job.error = result.error
    if job.status == "failed":
        refund_job(db, job)
    db.commit()
    db.refresh(job)
    return job


@router.get("", response_model=list[VideoJobOut])
def list_videos(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.scalars(
        select(VideoJob).where(VideoJob.user_id == user.id).order_by(VideoJob.id.desc())
    ).all()


@router.get("/{job_id}", response_model=VideoJobOut)
async def get_video(
    job_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    job = db.get(VideoJob, job_id)
    if job is None or job.user_id != user.id:
        raise HTTPException(status_code=404, detail="Video job not found")

    # 진행 중이면 제공자에게 최신 상태를 조회해서 갱신 (클라이언트 폴링 방식)
    if job.status in ACTIVE_STATUSES and job.external_id:
        try:
            result = await get_provider().fetch(job.external_id)
        except ProviderError:
            return job  # 일시적 오류는 무시하고 기존 상태 반환
        job.status = result.status
        job.video_url = result.video_url
        job.error = result.error
        if job.status == "failed":
            refund_job(db, job)
        db.commit()
        db.refresh(job)

    return job
