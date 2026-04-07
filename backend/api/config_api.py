from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import ConfigEntry

router = APIRouter(prefix="/config", tags=["config"])


@router.get("")
def get_config(db: Session = Depends(get_db)) -> dict:
    return {r.key: r.value for r in db.query(ConfigEntry).all()}


@router.put("")
def update_config(updates: dict[str, str], db: Session = Depends(get_db)) -> dict:
    for key, value in updates.items():
        entry = db.query(ConfigEntry).filter_by(key=key).first()
        if entry:
            entry.value = value
        else:
            db.add(ConfigEntry(key=key, value=value))
    db.commit()
    return {r.key: r.value for r in db.query(ConfigEntry).all()}
