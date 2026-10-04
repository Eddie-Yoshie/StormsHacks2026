import os

from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker, declarative_base

DB_NAME = os.getenv("DB_NAME", "ok")
DATABASE_URL = os.getenv(
    "DATABASE_URL", f"mysql+pymysql://root@127.0.0.1:4000/{DB_NAME}"
)
engine = create_engine(DATABASE_URL, echo=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# base class for models
base = declarative_base()


def init_db() -> None:
    """Create the target database (if missing) and all registered tables."""
    url = make_url(DATABASE_URL)
    server_engine = create_engine(url.set(database=""), echo=True)
    with server_engine.begin() as conn:
        conn.exec_driver_sql(f"CREATE DATABASE IF NOT EXISTS `{url.database}`")
    server_engine.dispose()

    from . import models  # noqa: F401  # register models on base.metadata

    base.metadata.create_all(engine)
