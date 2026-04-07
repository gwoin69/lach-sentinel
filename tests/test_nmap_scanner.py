import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.database import Base
from backend.models import Host, Service, ScanResult
from backend.modules.nmap_scanner import NmapScanner, parse_nmap_host


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


MOCK_HOST_DATA = {
    "status": {"state": "up"},
    "hostnames": [{"name": "router.local", "type": "PTR"}],
    "addresses": {"ipv4": "192.168.111.1", "mac": "aa:bb:cc:dd:ee:ff"},
    "vendor": {"aa:bb:cc:dd:ee:ff": "Apple"},
    "osmatch": [{"name": "Linux 5.x", "accuracy": "95"}],
    "tcp": {
        80: {"state": "open", "name": "http", "product": "nginx", "version": "1.24"},
        443: {"state": "open", "name": "https", "product": "nginx", "version": "1.24"},
    },
}


def test_parse_nmap_host_full():
    result = parse_nmap_host("192.168.111.1", MOCK_HOST_DATA)
    assert result["ip"] == "192.168.111.1"
    assert result["mac"] == "aa:bb:cc:dd:ee:ff"
    assert result["vendor"] == "Apple"
    assert result["hostname"] == "router.local"
    assert result["os"] == "Linux 5.x"
    assert len(result["services"]) == 2


def test_parse_nmap_host_no_mac():
    host = {**MOCK_HOST_DATA, "addresses": {"ipv4": "192.168.111.2"}, "vendor": {}}
    result = parse_nmap_host("192.168.111.2", host)
    assert result["mac"] is None
    assert result["vendor"] is None


def test_scan_inserts_new_host(session):
    scanner = NmapScanner(network_range="192.168.111.0/24")
    mock_nm = MagicMock()
    mock_nm.all_hosts.return_value = ["192.168.111.1"]
    mock_nm.__getitem__ = MagicMock(return_value=MOCK_HOST_DATA)
    with patch("backend.modules.nmap_scanner.nmap.PortScanner", return_value=mock_nm):
        scanner.scan(session)
    host = session.query(Host).filter_by(ip="192.168.111.1").first()
    assert host is not None
    assert host.status == "active"
    assert session.query(Service).filter_by(host_id=host.id).count() == 2


def test_scan_marks_absent_host(session):
    now = datetime.now(timezone.utc)
    existing = Host(ip="192.168.111.99", status="active", first_seen=now, last_seen=now)
    session.add(existing)
    session.commit()
    scanner = NmapScanner(network_range="192.168.111.0/24")
    mock_nm = MagicMock()
    mock_nm.all_hosts.return_value = []
    with patch("backend.modules.nmap_scanner.nmap.PortScanner", return_value=mock_nm):
        scanner.scan(session)
    session.refresh(existing)
    assert existing.status == "absent"


def test_scan_creates_completed_scan_result(session):
    scanner = NmapScanner(network_range="192.168.111.0/24")
    mock_nm = MagicMock()
    mock_nm.all_hosts.return_value = []
    with patch("backend.modules.nmap_scanner.nmap.PortScanner", return_value=mock_nm):
        scanner.scan(session)
    result = session.query(ScanResult).first()
    assert result is not None
    assert result.status == "completed"
    assert result.range == "192.168.111.0/24"
