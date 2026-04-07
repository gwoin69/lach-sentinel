import json
from fastapi import APIRouter, Depends
from sqlalchemy import desc
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Metric

router = APIRouter(prefix="/vms", tags=["vms"])


@router.get("")
def get_vms(db: Session = Depends(get_db)) -> list[dict]:
    row = db.query(Metric).filter(
        Metric.type == "vms", Metric.meta.isnot(None)
    ).order_by(desc(Metric.timestamp)).first()
    try:
        return json.loads(row.meta) if row else []
    except (json.JSONDecodeError, TypeError):
        return []
