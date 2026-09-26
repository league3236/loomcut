from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import get_settings


def _normalize_url(url: str) -> str:
    # Render는 postgres:// 형식으로 주므로 psycopg3 드라이버 형식으로 변환
    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url[len("postgres://"):]
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url[len("postgresql://"):]
    return url


DATABASE_URL = _normalize_url(get_settings().database_url)
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def add_missing_columns() -> None:
    """Alembic 도입 전 임시 마이그레이션: 모델에 새로 추가된 컴럼을 기존 테이블에 ADD COLUMN.

    새 컴럼은 nullable이거나 server_default가 있어야 한다.
    """
    insp = inspect(engine)
    existing_tables = set(insp.get_table_names())
    with engine.begin() as conn:
        for table in Base.metadata.sorted_tables:
            if table.name not in existing_tables:
                continue
            existing_cols = {c["name"] for c in insp.get_columns(table.name)}
            for col in table.columns:
                if col.name in existing_cols:
                    continue
                if not col.nullable and col.server_default is None:
                    raise RuntimeError(
                        f"Cannot auto-add NOT NULL column {table.name}.{col.name} without server_default"
                    )
                col_type = col.type.compile(dialect=engine.dialect)
                ddl = f"ALTER TABLE {table.name} ADD COLUMN {col.name} {col_type}"
                if col.server_default is not None:
                    ddl += f" DEFAULT {col.server_default.arg}"
                conn.execute(text(ddl))
