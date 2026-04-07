import asyncio
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from backend.models import Metric
from sqlalchemy import func

logger = logging.getLogger(__name__)
scheduler = AsyncIOScheduler()


def setup_scheduler(settings, db_factory, unraid_monitor, nmap_scanner, retention_job, ws_manager):
    async def collect_metrics():
        db = db_factory()
        try:
            await unraid_monitor.collect(db)
            subq = (
                db.query(Metric.type, func.max(Metric.timestamp).label("max_ts"))
                .group_by(Metric.type)
                .subquery()
            )
            latest_metrics = (
                db.query(Metric)
                .join(subq, (Metric.type == subq.c.type) & (Metric.timestamp == subq.c.max_ts))
                .all()
            )
            latest = {m.type: m.value for m in latest_metrics}
            await ws_manager.broadcast({"type": "metrics_update", "data": latest})
        finally:
            db.close()

    async def run_nmap():
        db = db_factory()
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, nmap_scanner.scan, db)
        finally:
            db.close()

    async def run_retention():
        db = db_factory()
        try:
            retention_job(db)
        finally:
            db.close()

    scheduler.add_job(
        collect_metrics, IntervalTrigger(seconds=settings.metrics_interval), id="collect_metrics"
    )
    scheduler.add_job(
        run_nmap, IntervalTrigger(seconds=settings.nmap_interval), id="nmap_scan"
    )
    scheduler.add_job(
        run_retention, IntervalTrigger(hours=1), id="retention"
    )
