from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, declarative_base

DATABASE_URL = make_url("mysql+pymysql://root@127.0.0.1:4000/ok");
engine = create_engine(DATABASE_URL, echo=True)
with engine.begin() as conn:
    conn.exec_driver_sql(f"CREATE DATABASE IF NOT EXISTS `{DATABASE_URL.database}`")

# base class for models
base = declarative_base()

def create_db_and_tables():
    base.metadata.create_all(engine)

def get_db():
    with Session(autocommit=False, autoflush=False, bind=engine) as db:
        yield db
