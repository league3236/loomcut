from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

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
    provider = get_provider()

    job = VideoJob(
        user_id=user.id,
        provider=provider.name,
        model=model,
        prompt=body.prompt,
        image_url=image_url,
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    try:
        result = await provider.submit(
            model=model, prompt=body.prompt, image_url=image_url, duration=body.duration
        )
    except (ProviderError, Exception) as e:  # noqa: BLE001
        job.status = "failed"
        job.error = str(e)
        db.commit()
        raise HTTPException(status_code=502, detail=f"Video provider error: {e}")

    job.external_id = result.external_id
    job.status = result.status
    job.video_url = result.video_url
    job.error = result.error
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
            job.status = result.status
            job.video_url = result.video_url
            job.error = result.error
            db.commit()
            db.refresh(job)
        except ProviderError:
            pass  # 일시적 오류는 무시하고 기존 상태 반환

    return job
