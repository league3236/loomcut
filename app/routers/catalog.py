from fastapi import APIRouter

from app.catalog import get_families
from app.config import get_settings
from app.schemas import ModelOut

router = APIRouter(prefix="/models", tags=["models"])


@router.get("", response_model=list[ModelOut])
def list_models():
    """선택 가능한 영상 모델과 초당 가격(크레딧)"""
    s = get_settings()
    return [
        ModelOut(
            key=f.key,
            name=f.name,
            description=f.description,
            price_per_second=f.price_per_second,
            price_for_default_duration=f.price_per_second * s.default_duration,
            default=f.key == s.default_model,
        )
        for f in get_families().values()
    ]
