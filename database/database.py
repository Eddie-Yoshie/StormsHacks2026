import os

from sqlalchemy import create_engine, inspect
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, declarative_base

SERVER_URL = os.environ.get("DATABASE_URL", "mysql+pymysql://root@127.0.0.1:4000");
server_engine = create_engine(SERVER_URL, echo=True)
with server_engine.begin() as conn:
    conn.exec_driver_sql(f"CREATE DATABASE IF NOT EXISTS ok")
server_engine.dispose()

db_url = make_url(SERVER_URL + "/ok")
engine = create_engine(db_url, echo=True)

# base class for models
base = declarative_base()

# create_all never alters a table that already exists, so columns added to a model later are added here.
_ADDED_COLUMNS = {
    "devices": {"noise_enabled": "BOOLEAN NOT NULL DEFAULT TRUE"},
}

def create_db_and_tables():
    base.metadata.create_all(engine)
    inspector = inspect(engine)
    with engine.begin() as conn:
        for table, columns in _ADDED_COLUMNS.items():
            existing = {column["name"] for column in inspector.get_columns(table)}
            for name, ddl in columns.items():
                if name not in existing:
                    conn.exec_driver_sql(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}")

def get_db():
    with Session(autocommit=False, autoflush=False, bind=engine) as db:
        yield db
