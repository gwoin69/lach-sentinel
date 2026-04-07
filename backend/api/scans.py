from fastapi import APIRouter, Depends, BackgroundTasks, Query
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import ScanResult, ConfigEntry
from backend.config import settings

router = APIRouter(prefix="/scans", tags=["scans"])


def scan_to_dict(s: ScanResult) -> dict:
    return {
        "id": s.id,
        "started_at": s.started_at.isoformat(),
        "finished_at": s.finished_at.isoformat() if s.finished_at else None,
        "range": s.range,
        "hosts_found": s.hosts_found,
        "status": s.status,
    }


@router.get("")
def list_scans(limit: int = Query(20, ge=1, le=200), db: Session = Depends(get_db)) -> list[dict]:
    rows = db.query(ScanResult).order_by(ScanResult.started_at.desc()).limit(limit).all()
    return [scan_to_dict(r) for r in rows]


@router.post("/trigger", status_code=202)
def trigger_scan(background_tasks: BackgroundTasks, db: Session = Depends(get_db)) -> dict:
    from backend.modules.nmap_scanner import NmapScanner
    config_entry = db.query(ConfigEntry).filter_by(key="nmap_range").first()
    nmap_range = config_entry.value if config_entry else settings.nmap_range
    scanner = NmapScanner(network_range=nmap_range)
    background_tasks.add_task(scanner.scan, db)
    return {"status": "scan_triggered", "range": nmap_range}
