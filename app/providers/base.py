from dataclasses import dataclass
from typing import Protocol


class ProviderError(Exception):
    pass


@dataclass
class GenerationResult:
    external_id: str | None
    status: str  # pending | processing | completed | failed
    video_url: str | None = None
    error: str | None = None


class VideoProvider(Protocol):
    """영상 생성 제공자 인터페이스. 새 모델/업체는 이 형태로 구현해서 추가."""

    name: str

    async def submit(
        self, *, model: str, prompt: str, image_url: str | None, duration: int | None
    ) -> GenerationResult: ...

    async def fetch(self, external_id: str) -> GenerationResult: ...
