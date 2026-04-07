import pytest
import os
os.environ["TESTING"] = "true"

from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.main import app
from backend.database import Base, get_db
from backend.models import Metric


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
        for i in range(5):
            db.add(Metric(timestamp=now - timedelta(minutes=i), type="cpu", value=20.0 + i))
        db.commit()
        db.close()
        yield c

    app.dependency_overrides.clear()


def test_get_current_metrics(client):
    resp = client.get("/api/v1/metrics/current")
    assert resp.status_code == 200
    assert "cpu" in resp.json()


def test_get_metrics_history_raw(client):
    resp = client.get("/api/v1/metrics/history?type=cpu&resolution=raw")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 5
    assert "timestamp" in data[0]
    assert "value" in data[0]


def test_get_metrics_history_unknown_type(client):
    resp = client.get("/api/v1/metrics/history?type=nonexistent&resolution=raw")
    assert resp.status_code == 200
    assert resp.json() == []
