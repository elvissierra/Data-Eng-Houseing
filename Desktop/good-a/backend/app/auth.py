from datetime import datetime, timedelta
from jose import jwt, JWTError
from fastapi import HTTPException, status, Depends
from fastapi.security import OAuth2PasswordBearer

# Dev secret — replace with env secret
SECRET = "dev-only-change-me"
ALGO = "HS256"
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

def create_tokens(user_id: int):
    now = datetime.utcnow()
    access = jwt.encode({"sub": user_id, "exp": now + timedelta(minutes=30)}, SECRET, algorithm=ALGO)
    refresh = jwt.encode({"sub": user_id, "exp": now + timedelta(days=30), "typ": "refresh"}, SECRET, algorithm=ALGO)
    return access, refresh

def verify_access_token(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET, algorithms=[ALGO])
        return payload
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

# Dependency to get current user id from access token
def get_current_user_id(token: dict = Depends(verify_access_token)) -> int:
    # 'sub' was set to the integer user_id in create_tokens
    return int(token["sub"])


# --- Auth router: register/login/refresh ---
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from passlib.hash import bcrypt
from .dependacies import get_db
from . import models
from .schemas import TokenPair, EmailStr

auth_router = APIRouter(prefix="/auth", tags=["auth"])

@auth_router.post("/register", response_model=TokenPair)
def register(email: EmailStr, password: str, db: Session = Depends(get_db)):
    existing = db.query(models.User).filter(models.User.email == email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    user = models.User(email=email, password_hash=bcrypt.hash(password))
    db.add(user); db.commit(); db.refresh(user)
    access, refresh = create_tokens(user.id)
    return TokenPair(access_token=access, refresh_token=refresh)

@auth_router.post("/login", response_model=TokenPair)
def login(email: EmailStr, password: str, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == email).first()
    if not user or not bcrypt.verify(password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    access, refresh = create_tokens(user.id)
    return TokenPair(access_token=access, refresh_token=refresh)

@auth_router.post("/refresh", response_model=TokenPair)
def refresh_token(refresh_token: str):
    # Accept refresh token and mint a new pair
    try:
        payload = jwt.decode(refresh_token, SECRET, algorithms=[ALGO])
        if payload.get("typ") != "refresh":
            raise JWTError("Not a refresh token")
        user_id = payload["sub"]
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    access, new_refresh = create_tokens(user_id)
    return TokenPair(access_token=access, refresh_token=new_refresh)