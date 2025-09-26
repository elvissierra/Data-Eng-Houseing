from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..dependacies import get_db, get_current_user_id
from .. import models, schemas

router = APIRouter(prefix="/activities", tags=["activities"])

@router.post("", response_model=schemas.ActivityOut)
def create_activity(payload: schemas.ActivityCreate, db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    act = models.Activity(user_id=user_id, **payload.model_dict(), source="manual")
    db.add(act); db.commit(); db.refresh(act)
    return schemas.ActivityOut(**payload.model_dict(), id=act.id, source=act.source, source_id=act.source_id, last_modified=act.last_modified)

@router.get("", response_model=list[schemas.ActivityOut])
def list_activities(db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    rows = db.query(models.Activity).filter(models.Activity.user_id==user_id).order_by(models.Activity.occurred_at.desc()).all()
    return [schemas.ActivityOut(id=r.id, type=r.type, minutes=r.minutes, intensity=r.intensity, note=r.note, occurred_at=r.occurred_at, source=r.source, source_id=r.source_id, last_modified=r.last_modified) for r in rows]