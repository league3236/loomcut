from app.config import get_settings
from app.providers.atlas import AtlasCloudProvider
from app.providers.base import GenerationResult, ProviderError, VideoProvider

__all__ = ["get_provider", "GenerationResult", "ProviderError", "VideoProvider"]


def get_provider() -> VideoProvider:
    s = get_settings()
    if s.video_provider == "atlas":
        return AtlasCloudProvider(api_key=s.atlas_api_key, base_url=s.atlas_base_url)
    raise ProviderError(f"Unknown video provider: {s.video_provider}")
