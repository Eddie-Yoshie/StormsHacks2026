from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, declarative_base

SERVER_URL = "mysql+pymysql://root@127.0.0.1:4000";
server_engine = create_engine(SERVER_URL, echo=True)
with server_engine.begin() as conn:
    conn.exec_driver_sql(f"CREATE DATABASE IF NOT EXISTS ok")
server_engine.dispose()

db_url = make_url(SERVER_URL + "/ok")
engine = create_engine(db_url, echo=True)

# base class for models
base = declarative_base()

def create_db_and_tables():
    base.metadata.create_all(engine)

def get_db():
    with Session(autocommit=False, autoflush=False, bind=engine) as db:
        yield db
