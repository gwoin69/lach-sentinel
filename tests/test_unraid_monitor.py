import pytest
from unittest.mock import patch, AsyncMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.database import Base
from backend.models import Metric
from backend.modules.unraid_monitor import UnraidMonitor


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


MOCK_CONTAINERS = [
    {"name": "nginx-proxy", "status": "running"},
    {"name": "plex", "status": "exited"},
]


@pytest.mark.asyncio
async def test_collect_writes_metrics(session):
    with (
        patch("backend.modules.unraid_monitor._read_cpu_percent", return_value=23.5),
        patch("backend.modules.unraid_monitor._read_meminfo",
              return_value={"MemTotal": 16000000, "MemAvailable": 8000000}),
        patch("backend.modules.unraid_monitor._read_cpu_temp", return_value=51.0),
        patch("backend.modules.unraid_monitor._read_uptime", return_value=1053840.0),
        patch("backend.modules.unraid_monitor._read_array_state", return_value="STARTED"),
        patch("backend.modules.unraid_monitor._read_array_capacity", return_value=(8.5, 17.5)),
        patch("backend.modules.unraid_monitor._get_containers",
              new=AsyncMock(return_value=MOCK_CONTAINERS)),
    ):
        await UnraidMonitor().collect(session)

    metrics = {m.type: m for m in session.query(Metric).all()}
    assert "cpu" in metrics
    assert metrics["cpu"].value == pytest.approx(23.5)
    assert "ram_used_gb" in metrics
    assert "temp_cpu" in metrics
    assert metrics["temp_cpu"].value == pytest.approx(51.0)
    assert "containers" in metrics
    assert metrics["containers"].value == 2.0
    assert "array_state" in metrics
    assert metrics["array_state"].meta == "STARTED"


@pytest.mark.asyncio
async def test_collect_handles_read_errors(session):
    """Toutes les lectures fichier échouent → metrics à zéro, pas d'exception."""
    with (
        patch("backend.modules.unraid_monitor._read_cpu_percent", return_value=0.0),
        patch("backend.modules.unraid_monitor._read_meminfo", return_value={}),
        patch("backend.modules.unraid_monitor._read_cpu_temp", return_value=0.0),
        patch("backend.modules.unraid_monitor._read_uptime", return_value=0.0),
        patch("backend.modules.unraid_monitor._read_array_state", return_value="unknown"),
        patch("backend.modules.unraid_monitor._read_array_capacity", return_value=(0.0, 0.0)),
        patch("backend.modules.unraid_monitor._get_containers",
              new=AsyncMock(return_value=[])),
    ):
        await UnraidMonitor().collect(session)

    assert session.query(Metric).count() > 0  # metrics écrites même avec valeurs nulles
