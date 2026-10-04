from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = make_url("mysql+pymysql://root@127.0.0.1:4000/ok");
engine = create_engine(DATABASE_URL, echo=True)
with engine.begin() as conn:
    conn.exec_driver_sql(f"CREATE DATABASE IF NOT EXISTS `{DATABASE_URL.database}`")

# base class for models
base = declarative_base()
base.metadata.create_all(engine)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
