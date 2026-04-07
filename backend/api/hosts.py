import json
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Host, Service

router = APIRouter(prefix="/hosts", tags=["hosts"])


class HostUpdate(BaseModel):
    label: str | None = None
    notes: str | None = None
    tags: list[str] | None = None
    monitoring_enabled: bool | None = None
    os: str | None = None


def host_to_dict(h: Host) -> dict:
    return {
        "id": h.id,
        "ip": h.ip,
        "hostname": h.hostname,
        "mac": h.mac,
        "vendor": h.vendor,
        "os": h.os,
        "status": h.status,
        "label": h.label,
        "notes": h.notes,
        "tags": json.loads(h.tags) if h.tags else [],
        "monitoring_enabled": h.monitoring_enabled,
        "first_seen": h.first_seen.isoformat(),
        "last_seen": h.last_seen.isoformat(),
    }


@router.get("")
def list_hosts(db: Session = Depends(get_db)) -> list[dict]:
    return [host_to_dict(h) for h in db.query(Host).order_by(Host.ip).all()]


@router.get("/{host_id}")
def get_host(host_id: int, db: Session = Depends(get_db)) -> dict:
    h = db.query(Host).filter_by(id=host_id).first()
    if not h:
        raise HTTPException(status_code=404, detail="Host not found")
    return host_to_dict(h)


@router.put("/{host_id}")
def update_host(host_id: int, body: HostUpdate, db: Session = Depends(get_db)) -> dict:
    h = db.query(Host).filter_by(id=host_id).first()
    if not h:
        raise HTTPException(status_code=404, detail="Host not found")
    if body.label is not None:
        h.label = body.label
    if body.notes is not None:
        h.notes = body.notes
    if body.tags is not None:
        h.tags = json.dumps(body.tags)
    if body.monitoring_enabled is not None:
        h.monitoring_enabled = body.monitoring_enabled
    if body.os is not None:
        h.os = body.os
    db.commit()
    db.refresh(h)
    return host_to_dict(h)


@router.delete("/{host_id}", status_code=204)
def delete_host(host_id: int, db: Session = Depends(get_db)) -> None:
    h = db.query(Host).filter_by(id=host_id).first()
    if not h:
        raise HTTPException(status_code=404, detail="Host not found")
    db.delete(h)
    db.commit()


@router.get("/{host_id}/services")
def list_services(host_id: int, db: Session = Depends(get_db)) -> list[dict]:
    h = db.query(Host).filter_by(id=host_id).first()
    if not h:
        raise HTTPException(status_code=404, detail="Host not found")
    return [
        {
            "id": s.id,
            "port": s.port,
            "protocol": s.protocol,
            "service_name": s.service_name,
            "version": s.version,
            "state": s.state,
            "last_seen": s.last_seen.isoformat() if s.last_seen else None,
        }
        for s in h.services
    ]
