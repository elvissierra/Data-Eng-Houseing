from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from fastapi import Depends, HTTPException, status
from .auth import verify_access_token

# e.g. postgresql+psycopg2://user:pass@host:5432/db
DATABASE_URL = "postgresql+psycopg2://postgres:postgres@localhost:5432/goodtoday"
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

def get_db():
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_current_user_id(token: str = Depends(verify_access_token)) -> int:
    # returns user_id from token claims
    return token["sub"]