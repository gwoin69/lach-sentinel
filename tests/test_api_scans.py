import pytest
import os
os.environ["TESTING"] = "true"

from datetime import datetime, timezone
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.main import app
from backend.database import Base, get_db
from backend.models import ScanResult, ConfigEntry


@pytest.fixture
def client():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine)

    def override_get_db():
        db = TestSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as c:
        db = TestSession()
        now = datetime.now(timezone.utc)
        db.add(ScanResult(started_at=now, finished_at=now, range="192.168.111.0/24",
                          hosts_found=5, status="completed"))
        db.add(ConfigEntry(key="nmap_range", value="192.168.111.0/24"))
        db.add(ConfigEntry(key="nmap_interval", value="3600"))
        db.commit()
        db.close()
        yield c

    app.dependency_overrides.clear()


def test_list_scans(client):
    resp = client.get("/api/v1/scans")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["hosts_found"] == 5
    assert data[0]["status"] == "completed"


def test_get_config(client):
    resp = client.get("/api/v1/config")
    assert resp.status_code == 200
    data = resp.json()
    assert data["nmap_range"] == "192.168.111.0/24"
    assert data["nmap_interval"] == "3600"


def test_update_config(client):
    resp = client.put("/api/v1/config", json={"nmap_interval": "7200"})
    assert resp.status_code == 200
    assert resp.json()["nmap_interval"] == "7200"
