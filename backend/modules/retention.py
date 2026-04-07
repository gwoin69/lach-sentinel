import logging
from datetime import datetime, timezone, timedelta
from sqlalchemy import text
from sqlalchemy.orm import Session
from backend.models import Metric, MetricHourly, MetricDaily

logger = logging.getLogger(__name__)

RAW_RETENTION_DAYS = 7
HOURLY_RETENTION_DAYS = 90
DAILY_RETENTION_DAYS = 365


def downsample_hourly(db: Session) -> None:
    """Agrège les métriques brutes de plus d'1h en métriques horaires."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=1)
    rows = db.execute(text("""
        SELECT type,
               strftime('%Y-%m-%dT%H:00:00', timestamp) AS hour,
               AVG(value) AS avg,
               MIN(value) AS min,
               MAX(value) AS max
        FROM metrics
        WHERE timestamp < :cutoff
        GROUP BY type, strftime('%Y-%m-%dT%H:00:00', timestamp)
    """), {"cutoff": cutoff}).fetchall()

    for row in rows:
        hour_dt = datetime.fromisoformat(row.hour).replace(tzinfo=timezone.utc)
        if not db.query(MetricHourly).filter_by(type=row.type, hour=hour_dt).first():
            db.add(MetricHourly(hour=hour_dt, type=row.type, avg=row.avg, min=row.min, max=row.max))
    db.commit()
    logger.debug("downsample_hourly: %d rows", len(rows))


def downsample_daily(db: Session) -> None:
    """Agrège les métriques horaires de plus de 3 mois en métriques journalières."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=HOURLY_RETENTION_DAYS)
    rows = db.execute(text("""
        SELECT type,
               date(hour) AS day,
               AVG(avg) AS avg,
               MIN(min) AS min,
               MAX(max) AS max
        FROM metrics_hourly
        WHERE hour < :cutoff
        GROUP BY type, date(hour)
    """), {"cutoff": cutoff}).fetchall()

    for row in rows:
        day_dt = datetime.strptime(row.day, "%Y-%m-%d").date()
        if not db.query(MetricDaily).filter_by(type=row.type, day=day_dt).first():
            db.add(MetricDaily(day=day_dt, type=row.type, avg=row.avg, min=row.min, max=row.max))
    db.commit()
    logger.debug("downsample_daily: %d rows", len(rows))


def purge_old_metrics(db: Session) -> None:
    """Supprime les métriques brutes > 7j et horaires > 3 mois."""
    raw_cutoff = datetime.now(timezone.utc) - timedelta(days=RAW_RETENTION_DAYS)
    hourly_cutoff = datetime.now(timezone.utc) - timedelta(days=HOURLY_RETENTION_DAYS)
    deleted_raw = db.query(Metric).filter(Metric.timestamp < raw_cutoff).delete()
    deleted_hourly = db.query(MetricHourly).filter(MetricHourly.hour < hourly_cutoff).delete()
    db.commit()
    logger.info("Purged %d raw, %d hourly metrics", deleted_raw, deleted_hourly)


def run_retention_job(db: Session) -> None:
    downsample_hourly(db)
    downsample_daily(db)
    purge_old_metrics(db)
