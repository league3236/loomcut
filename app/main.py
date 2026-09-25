from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import models  # noqa: F401  (테이블 등록용)
from app.config import get_settings
from app.database import Base, engine
from app.routers import auth, payments, videos


@asynccontextmanager
async def lifespan(app: FastAPI):
    # MVP 단계: 시작 시 테이블 자동 생성 (추후 Alembic 마이그레이션으로 전환)
    Base.metadata.create_all(bind=engine)
    yield


settings = get_settings()
app = FastAPI(title=settings.app_name, lifespan=lifespan)

origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials="*" not in origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(videos.router)
app.include_router(payments.router)


@app.get("/health", tags=["system"])
def health():
    return {"status": "ok"}
