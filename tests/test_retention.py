import pytest
from datetime import datetime, timezone, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.database import Base
from backend.models import Metric, MetricHourly, MetricDaily
from backend.modules.retention import downsample_hourly, downsample_daily, purge_old_metrics


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


def make_metrics(session, type_: str, hours_ago: int, count: int, base_value: float = 20.0):
    base = datetime.now(timezone.utc) - timedelta(hours=hours_ago)
    for i in range(count):
        session.add(Metric(
            timestamp=base + timedelta(minutes=i),
            type=type_,
            value=base_value + i,
        ))
    session.commit()


def test_downsample_hourly_creates_aggregate(session):
    make_metrics(session, "cpu", hours_ago=2, count=60)
    downsample_hourly(session)
    hourly = session.query(MetricHourly).all()
    assert len(hourly) >= 1
    assert hourly[0].type == "cpu"
    assert hourly[0].avg is not None
    assert hourly[0].min <= hourly[0].avg <= hourly[0].max


def test_downsample_hourly_skips_recent(session):
    make_metrics(session, "cpu", hours_ago=0, count=10)
    downsample_hourly(session)
    assert session.query(MetricHourly).count() == 0


def test_purge_old_raw_metrics(session):
    old = datetime.now(timezone.utc) - timedelta(days=8)
    for i in range(10):
        session.add(Metric(timestamp=old, type="cpu", value=float(i)))
    for i in range(5):
        session.add(Metric(timestamp=datetime.now(timezone.utc), type="cpu", value=float(i)))
    session.commit()
    purge_old_metrics(session)
    assert session.query(Metric).count() == 5


def test_downsample_daily_creates_aggregate(session):
    old_hour = datetime.now(timezone.utc) - timedelta(days=100)
    session.add(MetricHourly(hour=old_hour, type="cpu", avg=30.0, min=10.0, max=50.0))
    session.commit()
    downsample_daily(session)
    assert session.query(MetricDaily).count() == 1
