from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import ConfigEntry

router = APIRouter(prefix="/config", tags=["config"])

ALLOWED_KEYS = frozenset({
    "nmap_range",
    "nmap_interval",
    "metrics_interval",
    "UNRAID_HOST",
    "UNRAID_API_PORT",
    "UNRAID_API_KEY",
})

API_KEY_MASK = "***"


class ConfigUpdate(BaseModel):
    nmap_range: str | None = None
    nmap_interval: str | None = None
    metrics_interval: str | None = None
    UNRAID_HOST: str | None = None
    UNRAID_API_PORT: str | None = None
    UNRAID_API_KEY: str | None = None


def _mask_config(rows: list) -> dict:
    result = {}
    for r in rows:
        if r.key == "UNRAID_API_KEY":
            result[r.key] = API_KEY_MASK if r.value else ""
        else:
            result[r.key] = r.value
    return result


@router.get("")
def get_config(db: Session = Depends(get_db)) -> dict:
    return _mask_config(db.query(ConfigEntry).all())


@router.put("")
def update_config(updates: ConfigUpdate, db: Session = Depends(get_db)) -> dict:
    data = {k: v for k, v in updates.model_dump().items() if v is not None}
    for key, value in data.items():
        # Ne pas écraser la clé API si l'UI renvoie le masque inchangé
        if key == "UNRAID_API_KEY" and value == API_KEY_MASK:
            continue
        entry = db.query(ConfigEntry).filter_by(key=key).first()
        if entry:
            entry.value = value
        else:
            db.add(ConfigEntry(key=key, value=value))
    db.commit()
    return _mask_config(db.query(ConfigEntry).all())
