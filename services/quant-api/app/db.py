import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from .models import Base

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)
DB_PATH = Path(os.environ.get("QUANT_API_DB", str(DATA_DIR / "investment.db")))

engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def init_db() -> None:
    Base.metadata.create_all(engine)
    # SQLite create_all 不会给已存在表补索引，此处幂等地创建
    with engine.begin() as conn:
        conn.exec_driver_sql(
            "CREATE INDEX IF NOT EXISTS ix_trades_fund_code ON trades (fund_code)"
        )


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
