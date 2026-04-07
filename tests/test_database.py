import pytest
from datetime import datetime, timezone, date
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.database import Base
from backend.models import Metric, Host, Service, ScanResult, ConfigEntry


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
    Base.metadata.drop_all(engine)


def test_metric_insert(session):
    m = Metric(timestamp=datetime.now(timezone.utc), type="cpu", value=42.0)
    session.add(m)
    session.commit()
    result = session.query(Metric).first()
    assert result.value == 42.0
    assert result.type == "cpu"


def test_host_insert_and_defaults(session):
    now = datetime.now(timezone.utc)
    h = Host(ip="192.168.111.1", mac="aa:bb:cc:dd:ee:ff", vendor="Apple",
             status="active", first_seen=now, last_seen=now)
    session.add(h)
    session.commit()
    result = session.query(Host).filter_by(ip="192.168.111.1").first()
    assert result.vendor == "Apple"
    assert result.monitoring_enabled is True


def test_host_ip_unique(session):
    from sqlalchemy.exc import IntegrityError
    now = datetime.now(timezone.utc)
    session.add(Host(ip="10.0.0.1", first_seen=now, last_seen=now))
    session.commit()
    session.add(Host(ip="10.0.0.1", first_seen=now, last_seen=now))
    with pytest.raises(IntegrityError):
        session.commit()


def test_service_linked_to_host(session):
    now = datetime.now(timezone.utc)
    h = Host(ip="10.0.0.2", first_seen=now, last_seen=now)
    session.add(h)
    session.flush()
    session.add(Service(host_id=h.id, port=80, protocol="tcp", service_name="http"))
    session.commit()
    assert session.query(Service).filter_by(host_id=h.id).count() == 1


def test_config_entry(session):
    session.add(ConfigEntry(key="nmap_range", value="192.168.111.0/24"))
    session.commit()
    assert session.query(ConfigEntry).filter_by(key="nmap_range").first().value == "192.168.111.0/24"
