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
from backend.models import Host


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
        db.add(Host(ip="192.168.111.1", mac="aa:bb:cc:00:00:01", vendor="Apple",
                    status="active", first_seen=now, last_seen=now))
        db.add(Host(ip="192.168.111.2", status="absent", first_seen=now, last_seen=now))
        db.commit()
        db.close()
        yield c

    app.dependency_overrides.clear()


def test_list_hosts(client):
    resp = client.get("/api/v1/hosts")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


def test_get_host(client):
    resp = client.get("/api/v1/hosts/1")
    assert resp.status_code == 200
    data = resp.json()
    assert data["ip"] == "192.168.111.1"
    assert data["vendor"] == "Apple"
    assert data["tags"] == []


def test_get_host_not_found(client):
    assert client.get("/api/v1/hosts/9999").status_code == 404


def test_update_host_label_and_notes(client):
    resp = client.put("/api/v1/hosts/1", json={"label": "Mon routeur", "notes": "Routeur principal"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["label"] == "Mon routeur"
    assert data["notes"] == "Routeur principal"


def test_update_host_tags(client):
    resp = client.put("/api/v1/hosts/1", json={"tags": ["router", "important"]})
    assert resp.status_code == 200
    assert resp.json()["tags"] == ["router", "important"]


def test_delete_host(client):
    assert client.delete("/api/v1/hosts/2").status_code == 204
    assert client.get("/api/v1/hosts/2").status_code == 404
