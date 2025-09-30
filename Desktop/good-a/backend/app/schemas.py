from datetime import date, datetime
from pydantic import BaseModel, Field, EmailStr

class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class CheckinCreate(BaseModel):
    date: date
    mood: int = Field(ge=1, le=5)
    energy: int = Field(ge=1, le=5)
    note: str | None = None

class CheckinOut(CheckinCreate):
    id: int
    last_modified: datetime

class ActivityCreate(BaseModel):
    type: str
    minutes: int
    occurred_at: datetime
    intensity: int | None = None
    note: str | None = None

class ActivityOut(ActivityCreate):
    id: int
    source: str | None = None
    source_id: str | None = None
    last_modified: datetime