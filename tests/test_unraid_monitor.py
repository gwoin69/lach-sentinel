import pytest
from unittest.mock import patch
from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.database import Base
from backend.models import Metric
from backend.modules.unraid_monitor import UnraidMonitor, UnraidData


@pytest.fixture
def session():
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    s = Session()
    yield s
    s.close()


MOCK_RESPONSE = {
    "data": {
        "info": {
            "cpu": {"usage": 23.5},
            "memory": {"used": 14680064000, "total": 34359738368},
            "uptime": 1053840,
            "temperature": {"cpu": 51.0},
        },
        "array": {
            "state": "STARTED",
            "capacity": {"kilobytes": {"used": 14298974208, "total": 21474836480}},
            "parity": {"status": "VALID", "lastCheck": "2026-04-04T00:00:00Z"},
        },
        "docker": {
            "containers": [
                {"name": "nginx-proxy", "status": "running", "stats": {"cpu": 0.1, "memory": 12582912}},
                {"name": "plex", "status": "stopped", "stats": {"cpu": 0.0, "memory": 0}},
            ]
        },
        "vms": {
            "domains": [
                {"name": "Windows11", "status": "running", "vcpus": 4, "memory": 8589934592}
            ]
        },
    }
}


@pytest.mark.asyncio
async def test_fetch_parses_data():
    monitor = UnraidMonitor(host="192.168.111.253", api_key="test", verify_ssl=False)
    with patch.object(monitor, "_query", return_value=MOCK_RESPONSE):
        data = await monitor.fetch()
    assert data.cpu_usage == 23.5
    assert data.ram_used_gb == pytest.approx(14680064000 / 1024 ** 3, rel=1e-3)
    assert data.temp_cpu == 51.0
    assert len(data.containers) == 2
    assert len(data.vms) == 1


@pytest.mark.asyncio
async def test_collect_writes_metrics(session):
    monitor = UnraidMonitor(host="192.168.111.253", api_key="test", verify_ssl=False)
    with patch.object(monitor, "_query", return_value=MOCK_RESPONSE):
        await monitor.collect(session)
    types = {m.type for m in session.query(Metric).all()}
    assert "cpu" in types
    assert "ram_used_gb" in types
    assert "temp_cpu" in types
    assert "containers" in types
    assert "vms" in types


@pytest.mark.asyncio
async def test_collect_handles_connection_error(session):
    monitor = UnraidMonitor(host="192.168.111.253", api_key="test", verify_ssl=False)
    with patch.object(monitor, "_query", side_effect=Exception("Connection refused")):
        await monitor.collect(session)  # must not raise
    assert session.query(Metric).count() == 0
