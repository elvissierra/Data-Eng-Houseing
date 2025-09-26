from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import date
from ..dependacies import get_db, get_current_user_id
from .. import models, schemas

router = APIRouter(prefix="/checkins", tags=["checkins"])

@router.post("", response_model=schemas.CheckinOut)
def create_checkin(payload: schemas.CheckinCreate, db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    mc = models.MoodCheckin(user_id=user_id, **payload.model_dict())
    db.add(mc); db.commit(); db.refresh(mc)
    return schemas.CheckinOut(**payload.model_dict(), id=mc.id, last_modified=mc.last_modified)

@router.get("", response_model=list[schemas.CheckinOut])
def list_checkins(from_: date | None = None, to: date | None = None, db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    q = db.query(models.MoodCheckin).filter(models.MoodCheckin.user_id == user_id)
    if from_: q = q.filter(models.MoodCheckin.date >= from_)
    if to:    q = q.filter(models.MoodCheckin.date <= to)
    rows = q.order_by(models.MoodCheckin.date.desc()).all()
    return [schemas.CheckinOut(id=r.id, date=r.date, mood=r.mood, energy=r.energy, note=r.note, last_modified=r.last_modified) for r in rows]