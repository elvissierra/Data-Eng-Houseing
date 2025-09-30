from datetime import datetime, date
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import String, Integer, Date, DateTime, ForeignKey, Text

class Base(DeclarativeBase): pass

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class MoodCheckin(Base):
    __tablename__ = "mood_checkins"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    date: Mapped[date] = mapped_column(Date, index=True)
    mood: Mapped[int] = mapped_column(Integer)     # 1-5
    energy: Mapped[int] = mapped_column(Integer)   # 1-5
    note: Mapped[str | None] = mapped_column(Text, default=None)
    last_modified: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Activity(Base):
    __tablename__ = "activities"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    type: Mapped[str] = mapped_column(String(32))  # run|workout|brain|creative
    minutes: Mapped[int] = mapped_column(Integer)
    intensity: Mapped[int | None] = mapped_column(Integer)  # optional 1-5
    note: Mapped[str | None] = mapped_column(Text, default=None)
    occurred_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    source: Mapped[str | None] = mapped_column(String(32), default=None)  # manual|healthkit|googlefit
    source_id: Mapped[str | None] = mapped_column(String(64), default=None)
    last_modified: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)