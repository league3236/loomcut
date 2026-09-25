from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "loomcut"
    database_url: str = "sqlite:///./db.sqlite3"

    jwt_secret: str = "change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24

    # 어드민: 쉼표로 구분한 이메일 목록. 어드민은 크레딧 차감 없이 무료 생성
    admin_emails: str = ""

    # 과금: 영상 1초당 차감 크레딧 (1크레딧 = 1원)
    price_per_second: int = 400
    default_duration: int = 5

    # 토스페이먼츠
    toss_client_key: str = ""
    toss_secret_key: str = ""
    toss_base_url: str = "https://api.tosspayments.com"

    # 영상 생성 제공자 (현재 atlas만 구현, 추후 다른 제공자 추가 가능)
    video_provider: str = "atlas"
    atlas_api_key: str = ""
    atlas_base_url: str = "https://api.atlascloud.ai"
    default_t2v_model: str = "bytedance/seedance-2.0/text-to-video"
    default_i2v_model: str = "bytedance/seedance-2.0/image-to-video"

    cors_origins: str = "*"

    def admin_email_set(self) -> set[str]:
        return {e.strip().lower() for e in self.admin_emails.split(",") if e.strip()}


@lru_cache
def get_settings() -> Settings:
    return Settings()
