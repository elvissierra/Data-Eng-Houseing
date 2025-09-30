from fastapi import APIRouter, Depends
from datetime import date, timedelta
from sqlalchemy.orm import Session
from ..dependacies import get_db
from ..auth import get_current_user_id

router = APIRouter(prefix="/insights", tags=["insights"])

@router.get("/weekly")
def weekly(start: date | None = None, db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    if start is None:
        start = date.today() - timedelta(days=date.today().weekday())
    return {
        "week_start": str(start),
        "streaks": {"physical": 0, "mental": 0, "creative": 0, "social": 0},
        "balance": {"physical": 0, "mental": 0, "creative": 0, "social": 0},
        "highlights": []
    }