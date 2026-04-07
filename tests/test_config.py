import pytest
from backend.config import Settings


def test_default_values():
    s = Settings()
    assert s.unraid_host == "192.168.111.253"
    assert s.nmap_range == "192.168.111.0/24"
    assert s.nmap_interval == 3600
    assert s.metrics_interval == 60
    assert s.ws_push_interval == 5
    assert s.port == 8888


def test_env_override(monkeypatch):
    monkeypatch.setenv("NMAP_INTERVAL", "7200")
    s = Settings()
    assert s.nmap_interval == 7200
