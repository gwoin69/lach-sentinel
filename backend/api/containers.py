import json
from fastapi import APIRouter, Depends
from sqlalchemy import desc
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Metric

router = APIRouter(prefix="/containers", tags=["containers"])


@router.get("")
def get_containers(db: Session = Depends(get_db)) -> list[dict]:
    row = db.query(Metric).filter(
        Metric.type == "containers", Metric.meta.isnot(None)
    ).order_by(desc(Metric.timestamp)).first()
    return json.loads(row.meta) if row else []
