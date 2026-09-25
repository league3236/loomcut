from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "loomcut"
    database_url: str = "sqlite:///./db.sqlite3"

    jwt_secret: str = "change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24

    # 영상 생성 제공자 (현재 atlas만 구현, 추후 다른 제공자 추가 가능)
    video_provider: str = "atlas"
    atlas_api_key: str = ""
    atlas_base_url: str = "https://api.atlascloud.ai"
    default_t2v_model: str = "bytedance/seedance-2.0/text-to-video"
    default_i2v_model: str = "bytedance/seedance-2.0/image-to-video"

    cors_origins: str = "*"


@lru_cache
def get_settings() -> Settings:
    return Settings()
