from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.config import get_settings
from app.models import User
from app.providers import ProviderError, get_provider
from app.schemas import UploadOut
from app.security import get_current_user

router = APIRouter(prefix="/uploads", tags=["uploads"])

ALLOWED_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/gif",
    "image/bmp",
    "image/tiff",
}


@router.post("", response_model=UploadOut)
async def upload_image(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
):
    """이미지를 업로드하고 URL을 받는다. 받은 URL을 /videos의 이미지 필드에 사용."""
    content_type = file.content_type or ""
    if content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {content_type}")

    max_bytes = get_settings().max_upload_mb * 1024 * 1024
    content = await file.read(max_bytes + 1)
    if not content:
        raise HTTPException(status_code=400, detail="Empty file")
    if len(content) > max_bytes:
        raise HTTPException(status_code=413, detail="File too large")

    file_name = file.filename or "image"
    try:
        url = await get_provider().upload_media(file_name, content, content_type)
    except ProviderError as e:
        raise HTTPException(status_code=502, detail=str(e))

    return UploadOut(url=url, file_name=file_name, content_type=content_type, size=len(content))
