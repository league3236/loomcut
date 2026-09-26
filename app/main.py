from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import models  # noqa: F401  (테이블 등록용)
from app.config import get_settings
from app.database import Base, add_missing_columns, engine
from app.routers import auth, catalog, payments, uploads, videos


@asynccontextmanager
async def lifespan(app: FastAPI):
    # MVP 단계: 시작 시 테이블 생성 + 새 컴럼 추가 (추후 Alembic으로 전환)
    Base.metadata.create_all(bind=engine)
    add_missing_columns()
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
app.include_router(catalog.router)
app.include_router(uploads.router)
app.include_router(videos.router)
app.include_router(payments.router)


@app.get("/health", tags=["system"])
def health():
    return {"status": "ok"}
