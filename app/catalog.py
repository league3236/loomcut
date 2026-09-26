"""선택 가능한 영상 모델 목록과 모델별 가격.

사용자는 모델 '패밀리'(예: seedance-2.0-mini)만 고르고,
입력에 따라 제공자의 실제 모델 ID(text/image/reference-to-video)가 자동 결정된다.
"""

from dataclasses import dataclass

from app.config import get_settings

# 생성 모드 → 제공자 모델 경로
MODES = {
    "text": "text-to-video",  # 프롬프트만
    "image": "image-to-video",  # 참고 이미지(첫 장면, 선택적으로 마지막 장면)
    "reference": "reference-to-video",  # 레퍼런스 이미지(최대 9장)
}


@dataclass(frozen=True)
class ModelFamily:
    key: str
    name: str
    description: str
    provider_prefix: str
    price_per_second: int


def get_families() -> dict[str, ModelFamily]:
    s = get_settings()
    families = [
        ModelFamily(
            key="seedance-2.0",
            name="Seedance 2.0",
            description="최고 품질",
            provider_prefix="bytedance/seedance-2.0",
            price_per_second=s.price_per_second,
        ),
        ModelFamily(
            key="seedance-2.0-fast",
            name="Seedance 2.0 Fast",
            description="빠른 생성, 합리적인 가격",
            provider_prefix="bytedance/seedance-2.0-fast",
            price_per_second=s.price_per_second_fast,
        ),
        ModelFamily(
            key="seedance-2.0-mini",
            name="Seedance 2.0 Mini",
            description="가장 저렴한 가격",
            provider_prefix="bytedance/seedance-2.0-mini",
            price_per_second=s.price_per_second_mini,
        ),
    ]
    return {f.key: f for f in families}


def resolve_mode(first_frame_image: str | None, reference_images: list[str]) -> str:
    if reference_images:
        return "reference"
    if first_frame_image:
        return "image"
    return "text"


def provider_model_id(family: ModelFamily, mode: str) -> str:
    return f"{family.provider_prefix}/{MODES[mode]}"
