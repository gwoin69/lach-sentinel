from datetime import datetime, timezone, timedelta
from typing import Literal
from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Metric, MetricHourly, MetricDaily

router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get("/current")
def get_current_metrics(db: Session = Depends(get_db)) -> dict:
    subq = (
        db.query(Metric.type, func.max(Metric.timestamp).label("max_ts"))
        .group_by(Metric.type)
        .subquery()
    )
    rows = (
        db.query(Metric)
        .join(subq, (Metric.type == subq.c.type) & (Metric.timestamp == subq.c.max_ts))
        .all()
    )
    return {m.type: m.value for m in rows}


@router.get("/history")
def get_metrics_history(
    type: str = Query(...),
    resolution: Literal["raw", "hourly", "daily"] = Query("raw"),
    from_: datetime | None = Query(None, alias="from"),
    to: datetime | None = Query(None),
    db: Session = Depends(get_db),
) -> list[dict]:
    to = to or datetime.now(timezone.utc)
    from_ = from_ or (to - timedelta(hours=24))

    if resolution == "raw":
        rows = db.query(Metric).filter(
            Metric.type == type, Metric.timestamp >= from_, Metric.timestamp <= to
        ).order_by(Metric.timestamp).all()
        return [{"timestamp": r.timestamp.isoformat(), "value": r.value} for r in rows]

    if resolution == "hourly":
        rows = db.query(MetricHourly).filter(
            MetricHourly.type == type, MetricHourly.hour >= from_, MetricHourly.hour <= to
        ).order_by(MetricHourly.hour).all()
        return [{"timestamp": r.hour.isoformat(), "avg": r.avg, "min": r.min, "max": r.max} for r in rows]

    rows = db.query(MetricDaily).filter(
        MetricDaily.type == type,
        MetricDaily.day >= from_.date(),
        MetricDaily.day <= to.date(),
    ).order_by(MetricDaily.day).all()
    return [{"timestamp": r.day.isoformat(), "avg": r.avg, "min": r.min, "max": r.max} for r in rows]
