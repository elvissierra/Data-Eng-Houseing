from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import datetime
from ..dependacies import get_db
from ..auth import get_current_user_id
from .. import models

router = APIRouter(prefix="/sync", tags=["sync"])

@router.post("/push")
def push_ops(ops: dict, db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    # MVP: accept operations like [{"op":"upsert_checkin", "data": {...}, "client_id":"...", "op_id":"..."}]
    # Persist, ignore duplicates based on (client_id, op_id) if you add a server table later.
    return {"accepted": len(ops.get("ops", []))}

@router.get("/pull")
def pull_since(since: datetime, db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    # return deltas
    # Simplified: fetch all modified after 'since'
    return {
        "checkins": [],
        "activities": [],
        "server_time": datetime.utcnow().isoformat() + "Z"
    }