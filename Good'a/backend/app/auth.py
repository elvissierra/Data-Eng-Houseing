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