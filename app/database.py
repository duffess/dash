from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.config import get_settings

DATABASE_URL = get_settings().database_url

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
    if "sqlite" in DATABASE_URL else {}
)

# session local

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# base pra models

Base = declarative_base()

#dependency pra usar nas rota

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
