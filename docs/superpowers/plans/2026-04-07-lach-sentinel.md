# lach-sentinel Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a single-container Docker app pour Unraid v7.1.4 — monitoring temps réel (système, Docker, VMs) et découverte réseau Nmap — avec dashboard Vue.js.

**Architecture:** FastAPI (Python 3.12) sert REST API, WebSocket et assets Vue.js statiques depuis un seul conteneur. APScheduler orchestre le polling Unraid (60s) et les scans Nmap (fréquence réglable). SQLite stocke tout avec rétention 3 niveaux (brut 7j → horaire 3m → journalier 1an). Nmap nécessite NET_ADMIN + NET_RAW.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2, APScheduler 3.x, python-nmap, httpx, pydantic-settings ; Vue 3, Vite, TypeScript, Pinia, Vue Router, Chart.js ; Docker multi-stage build.

---

## Structure des fichiers

```
lach-sentinel/
├── backend/
│   ├── main.py              # App FastAPI, lifespan, WebSocket endpoint, SPA fallback
│   ├── config.py            # Pydantic-settings : toutes les variables d'env
│   ├── database.py          # Engine SQLAlchemy + SessionLocal + init_db()
│   ├── models.py            # Tous les modèles ORM
│   ├── scheduler.py         # APScheduler + enregistrement des jobs
│   ├── api/
│   │   ├── __init__.py      # APIRouter agrégateur
│   │   ├── metrics.py       # GET /api/v1/metrics/current + /history
│   │   ├── containers.py    # GET /api/v1/containers
│   │   ├── vms.py           # GET /api/v1/vms
│   │   ├── hosts.py         # CRUD /api/v1/hosts + /{id}/services
│   │   ├── scans.py         # GET/POST /api/v1/scans + /trigger
│   │   └── config_api.py    # GET/PUT /api/v1/config
│   ├── ws/
│   │   ├── __init__.py
│   │   └── manager.py       # WebSocketManager : connect/disconnect/broadcast
│   └── modules/
│       ├── __init__.py
│       ├── unraid_monitor.py  # collect() → écrit métriques en DB
│       ├── nmap_scanner.py    # scan() → upsert hosts/services/scan_results
│       ├── retention.py       # downsample + purge automatiques
│       └── alert_engine.py    # stub async send_alert() pour v2
├── frontend/
│   ├── package.json
│   ├── vite.config.ts
│   ├── tsconfig.json
│   ├── index.html
│   └── src/
│       ├── main.ts
│       ├── App.vue
│       ├── router/index.ts
│       ├── stores/
│       │   ├── metrics.ts       # Pinia : métriques courantes + historique
│       │   ├── hosts.ts         # Pinia : CRUD hôtes
│       │   └── ws.ts            # Pinia : WebSocket + reconnexion
│       ├── views/
│       │   ├── Dashboard.vue
│       │   ├── UnraidView.vue
│       │   ├── ContainersView.vue
│       │   ├── VmsView.vue
│       │   ├── NetworkView.vue
│       │   ├── HostsView.vue
│       │   ├── ScansView.vue
│       │   └── SettingsView.vue
│       └── components/
│           ├── layout/
│           │   ├── AppLayout.vue
│           │   └── Sidebar.vue
│           ├── widgets/
│           │   ├── KpiCard.vue
│           │   ├── StorageWidget.vue
│           │   ├── ContainersWidget.vue
│           │   ├── VmsWidget.vue
│           │   └── NetworkWidget.vue
│           └── hosts/
│               ├── HostTable.vue
│               └── HostEditModal.vue
├── tests/
│   ├── conftest.py
│   ├── test_config.py
│   ├── test_database.py
│   ├── test_unraid_monitor.py
│   ├── test_nmap_scanner.py
│   ├── test_retention.py
│   ├── test_ws_manager.py
│   ├── test_api_metrics.py
│   ├── test_api_hosts.py
│   └── test_api_scans.py
├── Dockerfile
├── docker-compose.yml
├── .dockerignore
├── .env.example
├── pytest.ini
├── requirements.txt
└── requirements-dev.txt
```

---

## Task 1 : Scaffolding + configuration

**Files:**
- Create: `requirements.txt`
- Create: `requirements-dev.txt`
- Create: `pytest.ini`
- Create: `backend/__init__.py`
- Create: `backend/config.py`
- Create: `.env.example`
- Create: `tests/conftest.py`
- Create: `tests/test_config.py`

- [ ] **Step 1.1 : Créer `requirements.txt`**

```
fastapi==0.111.0
uvicorn[standard]==0.29.0
sqlalchemy==2.0.30
pydantic-settings==2.2.1
apscheduler==3.10.4
python-nmap==0.7.1
httpx==0.27.0
websockets==12.0
```

- [ ] **Step 1.2 : Créer `requirements-dev.txt`**

```
pytest==8.2.0
pytest-asyncio==0.23.6
httpx==0.27.0
```

- [ ] **Step 1.3 : Créer `pytest.ini`**

```ini
[pytest]
asyncio_mode = auto
```

- [ ] **Step 1.4 : Écrire le test échouant pour config**

Créer `tests/test_config.py` :

```python
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
```

- [ ] **Step 1.5 : Lancer le test pour vérifier l'échec**

```bash
cd /home/fozzy/claude/lach-sentinel
pip install -r requirements.txt -r requirements-dev.txt
pytest tests/test_config.py -v
```
Attendu : `ModuleNotFoundError: No module named 'backend'`

- [ ] **Step 1.6 : Créer `backend/__init__.py`** (vide)

- [ ] **Step 1.7 : Créer `backend/config.py`**

```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    unraid_host: str = "192.168.111.253"
    unraid_api_port: int = 7443
    unraid_api_key: str = ""
    nmap_range: str = "192.168.111.0/24"
    nmap_interval: int = 3600
    metrics_interval: int = 60
    ws_push_interval: int = 5
    port: int = 8888
    tz: str = "Europe/Paris"
    database_url: str = "sqlite:////data/sentinel.db"
    testing: bool = False


settings = Settings()
```

- [ ] **Step 1.8 : Créer `.env.example`**

```
UNRAID_HOST=192.168.111.253
UNRAID_API_PORT=7443
UNRAID_API_KEY=your_api_key_here
NMAP_RANGE=192.168.111.0/24
NMAP_INTERVAL=3600
METRICS_INTERVAL=60
WS_PUSH_INTERVAL=5
TZ=Europe/Paris
```

- [ ] **Step 1.9 : Créer `tests/conftest.py`**

```python
import os
os.environ["TESTING"] = "true"  # Doit être avant tout import backend

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


@pytest.fixture(scope="function")
def test_engine():
    from backend.database import Base
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)


@pytest.fixture(scope="function")
def db_session(test_engine):
    Session = sessionmaker(bind=test_engine)
    session = Session()
    yield session
    session.close()
```

- [ ] **Step 1.10 : Lancer les tests**

```bash
pytest tests/test_config.py -v
```
Attendu : 2 tests PASS

- [ ] **Step 1.11 : Commit**

```bash
git init
git add .
git commit -m "feat: project scaffolding and configuration"
```

---

## Task 2 : Modèles de base de données

**Files:**
- Create: `backend/database.py`
- Create: `backend/models.py`
- Create: `tests/test_database.py`

- [ ] **Step 2.1 : Écrire les tests échouants**

Créer `tests/test_database.py` :

```python
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
```

- [ ] **Step 2.2 : Lancer pour vérifier l'échec**

```bash
pytest tests/test_database.py -v
```
Attendu : `ImportError` (modules pas encore créés)

- [ ] **Step 2.3 : Créer `backend/database.py`**

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from backend.config import settings


class Base(DeclarativeBase):
    pass


engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    Base.metadata.create_all(bind=engine)
```

- [ ] **Step 2.4 : Créer `backend/models.py`**

```python
from datetime import datetime, date as date_type
from sqlalchemy import Integer, Float, String, Boolean, DateTime, Date, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.database import Base


class Metric(Base):
    __tablename__ = "metrics"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    meta: Mapped[str | None] = mapped_column(Text)


class MetricHourly(Base):
    __tablename__ = "metrics_hourly"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    hour: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    avg: Mapped[float | None] = mapped_column(Float)
    min: Mapped[float | None] = mapped_column(Float)
    max: Mapped[float | None] = mapped_column(Float)


class MetricDaily(Base):
    __tablename__ = "metrics_daily"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    day: Mapped[date_type] = mapped_column(Date, nullable=False, index=True)
    type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    avg: Mapped[float | None] = mapped_column(Float)
    min: Mapped[float | None] = mapped_column(Float)
    max: Mapped[float | None] = mapped_column(Float)


class Host(Base):
    __tablename__ = "hosts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ip: Mapped[str] = mapped_column(String(45), nullable=False, unique=True)
    hostname: Mapped[str | None] = mapped_column(String(255))
    mac: Mapped[str | None] = mapped_column(String(17))
    vendor: Mapped[str | None] = mapped_column(String(128))
    os: Mapped[str | None] = mapped_column(String(128))
    status: Mapped[str] = mapped_column(String(16), default="active")
    label: Mapped[str | None] = mapped_column(String(128))
    notes: Mapped[str | None] = mapped_column(Text)
    tags: Mapped[str | None] = mapped_column(Text)  # JSON array serialisé
    monitoring_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    first_seen: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    last_seen: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    services: Mapped[list["Service"]] = relationship(
        "Service", back_populates="host", cascade="all, delete-orphan"
    )


class Service(Base):
    __tablename__ = "services"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    host_id: Mapped[int] = mapped_column(Integer, ForeignKey("hosts.id"), nullable=False)
    port: Mapped[int] = mapped_column(Integer, nullable=False)
    protocol: Mapped[str] = mapped_column(String(8), nullable=False)
    service_name: Mapped[str | None] = mapped_column(String(64))
    version: Mapped[str | None] = mapped_column(String(128))
    state: Mapped[str | None] = mapped_column(String(16))
    last_seen: Mapped[datetime | None] = mapped_column(DateTime)
    host: Mapped["Host"] = relationship("Host", back_populates="services")


class ScanResult(Base):
    __tablename__ = "scan_results"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime)
    range: Mapped[str] = mapped_column(String(64), nullable=False)
    hosts_found: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(16), default="running")
    raw_output: Mapped[str | None] = mapped_column(Text)


class ConfigEntry(Base):
    __tablename__ = "config"
    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
```

- [ ] **Step 2.5 : Lancer les tests**

```bash
pytest tests/test_database.py -v
```
Attendu : 5 tests PASS

- [ ] **Step 2.6 : Commit**

```bash
git add backend/database.py backend/models.py tests/test_database.py tests/conftest.py
git commit -m "feat: database models and schema"
```

---

## Task 3 : Module Unraid Monitor

**Files:**
- Create: `backend/modules/__init__.py`
- Create: `backend/modules/unraid_monitor.py`
- Create: `tests/test_unraid_monitor.py`

- [ ] **Step 3.1 : Écrire les tests échouants**

Créer `tests/test_unraid_monitor.py` :

```python
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
        await monitor.collect(session)  # ne doit pas lever d'exception
    assert session.query(Metric).count() == 0
```

- [ ] **Step 3.2 : Lancer pour vérifier l'échec**

```bash
pytest tests/test_unraid_monitor.py -v
```
Attendu : `ImportError`

- [ ] **Step 3.3 : Créer `backend/modules/__init__.py`** (vide)

- [ ] **Step 3.4 : Créer `backend/modules/unraid_monitor.py`**

```python
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone

import httpx
from sqlalchemy.orm import Session

from backend.models import Metric

logger = logging.getLogger(__name__)

GRAPHQL_QUERY = """
query {
  info {
    cpu { usage }
    memory { used total }
    uptime
    temperature { cpu }
  }
  array {
    state
    capacity { kilobytes { used total } }
    parity { status lastCheck }
  }
  docker {
    containers {
      name status
      stats { cpu memory }
    }
  }
  vms {
    domains { name status vcpus memory }
  }
}
"""


@dataclass
class UnraidData:
    cpu_usage: float = 0.0
    ram_used_gb: float = 0.0
    ram_total_gb: float = 0.0
    temp_cpu: float = 0.0
    uptime_seconds: int = 0
    array_state: str = "unknown"
    array_used_tb: float = 0.0
    array_total_tb: float = 0.0
    containers: list[dict] = field(default_factory=list)
    vms: list[dict] = field(default_factory=list)


class UnraidMonitor:
    def __init__(self, host: str, api_key: str, api_port: int = 7443, verify_ssl: bool = False):
        self.base_url = f"https://{host}:{api_port}/graphql"
        self.headers = {"x-api-key": api_key, "Content-Type": "application/json"}
        self.verify_ssl = verify_ssl

    async def _query(self, query: str) -> dict:
        async with httpx.AsyncClient(verify=self.verify_ssl, timeout=10.0) as client:
            resp = await client.post(
                self.base_url, json={"query": query}, headers=self.headers
            )
            resp.raise_for_status()
            return resp.json()

    async def fetch(self) -> UnraidData:
        raw = await self._query(GRAPHQL_QUERY)
        d = raw["data"]
        return UnraidData(
            cpu_usage=d["info"]["cpu"]["usage"],
            ram_used_gb=d["info"]["memory"]["used"] / 1024 ** 3,
            ram_total_gb=d["info"]["memory"]["total"] / 1024 ** 3,
            temp_cpu=d["info"]["temperature"]["cpu"],
            uptime_seconds=d["info"]["uptime"],
            array_state=d["array"]["state"],
            array_used_tb=d["array"]["capacity"]["kilobytes"]["used"] / 1024 ** 3,
            array_total_tb=d["array"]["capacity"]["kilobytes"]["total"] / 1024 ** 3,
            containers=d["docker"]["containers"],
            vms=d["vms"]["domains"],
        )

    async def collect(self, db: Session) -> None:
        try:
            data = await self.fetch()
        except Exception as exc:
            logger.error("Unraid Monitor fetch failed: %s", exc)
            return

        now = datetime.now(timezone.utc)
        metrics = [
            Metric(timestamp=now, type="cpu", value=data.cpu_usage),
            Metric(timestamp=now, type="ram_used_gb", value=data.ram_used_gb),
            Metric(timestamp=now, type="ram_total_gb", value=data.ram_total_gb),
            Metric(timestamp=now, type="temp_cpu", value=data.temp_cpu),
            Metric(timestamp=now, type="uptime_seconds", value=float(data.uptime_seconds)),
            Metric(timestamp=now, type="array_used_tb", value=data.array_used_tb),
            Metric(timestamp=now, type="array_total_tb", value=data.array_total_tb),
            Metric(
                timestamp=now,
                type="containers",
                value=float(len(data.containers)),
                meta=json.dumps(data.containers),
            ),
            Metric(
                timestamp=now,
                type="vms",
                value=float(len(data.vms)),
                meta=json.dumps(data.vms),
            ),
        ]
        db.add_all(metrics)
        db.commit()
        logger.debug("Unraid metrics collected: cpu=%.1f%%", data.cpu_usage)
```

- [ ] **Step 3.5 : Lancer les tests**

```bash
pytest tests/test_unraid_monitor.py -v
```
Attendu : 3 tests PASS

- [ ] **Step 3.6 : Commit**

```bash
git add backend/modules/ tests/test_unraid_monitor.py
git commit -m "feat: Unraid Monitor module with GraphQL client and metric persistence"
```

---

## Task 4 : Module Nmap Scanner

**Files:**
- Create: `backend/modules/nmap_scanner.py`
- Create: `tests/test_nmap_scanner.py`

- [ ] **Step 4.1 : Écrire les tests échouants**

Créer `tests/test_nmap_scanner.py` :

```python
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
```

- [ ] **Step 4.2 : Lancer pour vérifier l'échec**

```bash
pytest tests/test_nmap_scanner.py -v
```
Attendu : `ImportError`

- [ ] **Step 4.3 : Créer `backend/modules/nmap_scanner.py`**

```python
import logging
from datetime import datetime, timezone

import nmap
from sqlalchemy.orm import Session

from backend.models import Host, Service, ScanResult

logger = logging.getLogger(__name__)

NMAP_ARGS = "-O -sV --osscan-guess"


def parse_nmap_host(ip: str, host_data: dict) -> dict:
    addresses = host_data.get("addresses", {})
    mac = addresses.get("mac")
    vendor_map = host_data.get("vendor", {})
    vendor = vendor_map.get(mac) if mac else None

    hostnames = host_data.get("hostnames", [])
    hostname = hostnames[0]["name"] if hostnames and hostnames[0].get("name") else None

    osmatches = host_data.get("osmatch", [])
    os_name = osmatches[0]["name"] if osmatches else None

    services = []
    for port, port_data in host_data.get("tcp", {}).items():
        product = port_data.get("product", "")
        version = port_data.get("version", "")
        full_version = f"{product} {version}".strip() or None
        services.append({
            "port": port,
            "protocol": "tcp",
            "service_name": port_data.get("name"),
            "version": full_version,
            "state": port_data.get("state"),
        })

    return {"ip": ip, "hostname": hostname, "mac": mac, "vendor": vendor, "os": os_name, "services": services}


class NmapScanner:
    def __init__(self, network_range: str, nmap_args: str = NMAP_ARGS):
        self.network_range = network_range
        self.nmap_args = nmap_args

    def scan(self, db: Session) -> ScanResult:
        started = datetime.now(timezone.utc)
        scan_record = ScanResult(started_at=started, range=self.network_range, status="running")
        db.add(scan_record)
        db.commit()

        try:
            nm = nmap.PortScanner()
            nm.scan(hosts=self.network_range, arguments=self.nmap_args)
            found_ips = set(nm.all_hosts())
            now = datetime.now(timezone.utc)

            for ip in found_ips:
                parsed = parse_nmap_host(ip, nm[ip])
                existing = db.query(Host).filter_by(ip=ip).first()

                if existing:
                    existing.last_seen = now
                    existing.status = "active"
                    existing.hostname = parsed["hostname"] or existing.hostname
                    existing.mac = parsed["mac"] or existing.mac
                    existing.vendor = parsed["vendor"] or existing.vendor
                    existing.os = parsed["os"] or existing.os
                else:
                    existing = Host(
                        ip=ip,
                        hostname=parsed["hostname"],
                        mac=parsed["mac"],
                        vendor=parsed["vendor"],
                        os=parsed["os"],
                        status="active",
                        first_seen=now,
                        last_seen=now,
                    )
                    db.add(existing)
                    db.flush()

                for svc in parsed["services"]:
                    existing_svc = db.query(Service).filter_by(
                        host_id=existing.id, port=svc["port"], protocol=svc["protocol"]
                    ).first()
                    if existing_svc:
                        existing_svc.last_seen = now
                        existing_svc.state = svc["state"]
                    else:
                        db.add(Service(host_id=existing.id, last_seen=now, **svc))

            # Marquer les hôtes absents
            db.query(Host).filter(
                Host.status == "active",
                Host.ip.notin_(found_ips),
            ).update({"status": "absent"}, synchronize_session=False)

            scan_record.finished_at = datetime.now(timezone.utc)
            scan_record.hosts_found = len(found_ips)
            scan_record.status = "completed"
            db.commit()
            logger.info("Nmap scan completed: %d hosts on %s", len(found_ips), self.network_range)

        except Exception as exc:
            logger.error("Nmap scan failed: %s", exc)
            scan_record.status = "failed"
            scan_record.finished_at = datetime.now(timezone.utc)
            db.commit()

        return scan_record
```

- [ ] **Step 4.4 : Lancer les tests**

```bash
pytest tests/test_nmap_scanner.py -v
```
Attendu : 5 tests PASS

- [ ] **Step 4.5 : Commit**

```bash
git add backend/modules/nmap_scanner.py tests/test_nmap_scanner.py
git commit -m "feat: Nmap scanner module with host upsert, service tracking, and scan history"
```

---

## Task 5 : Module Rétention SQLite

**Files:**
- Create: `backend/modules/retention.py`
- Create: `tests/test_retention.py`

- [ ] **Step 5.1 : Écrire les tests échouants**

Créer `tests/test_retention.py` :

```python
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
```

- [ ] **Step 5.2 : Lancer pour vérifier l'échec**

```bash
pytest tests/test_retention.py -v
```
Attendu : `ImportError`

- [ ] **Step 5.3 : Créer `backend/modules/retention.py`**

```python
import logging
from datetime import datetime, timezone, timedelta
from sqlalchemy import text
from sqlalchemy.orm import Session
from backend.models import Metric, MetricHourly, MetricDaily

logger = logging.getLogger(__name__)

RAW_RETENTION_DAYS = 7
HOURLY_RETENTION_DAYS = 90
DAILY_RETENTION_DAYS = 365


def downsample_hourly(db: Session) -> None:
    """Agrège les métriques brutes de plus d'1h en métriques horaires."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=1)
    rows = db.execute(text("""
        SELECT type,
               strftime('%Y-%m-%dT%H:00:00', timestamp) AS hour,
               AVG(value) AS avg,
               MIN(value) AS min,
               MAX(value) AS max
        FROM metrics
        WHERE timestamp < :cutoff
        GROUP BY type, strftime('%Y-%m-%dT%H:00:00', timestamp)
    """), {"cutoff": cutoff}).fetchall()

    for row in rows:
        hour_dt = datetime.fromisoformat(row.hour).replace(tzinfo=timezone.utc)
        if not db.query(MetricHourly).filter_by(type=row.type, hour=hour_dt).first():
            db.add(MetricHourly(hour=hour_dt, type=row.type, avg=row.avg, min=row.min, max=row.max))
    db.commit()
    logger.debug("downsample_hourly: %d rows", len(rows))


def downsample_daily(db: Session) -> None:
    """Agrège les métriques horaires de plus de 3 mois en métriques journalières."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=HOURLY_RETENTION_DAYS)
    rows = db.execute(text("""
        SELECT type,
               date(hour) AS day,
               AVG(avg) AS avg,
               MIN(min) AS min,
               MAX(max) AS max
        FROM metrics_hourly
        WHERE hour < :cutoff
        GROUP BY type, date(hour)
    """), {"cutoff": cutoff}).fetchall()

    for row in rows:
        day_dt = datetime.strptime(row.day, "%Y-%m-%d").date()
        if not db.query(MetricDaily).filter_by(type=row.type, day=day_dt).first():
            db.add(MetricDaily(day=day_dt, type=row.type, avg=row.avg, min=row.min, max=row.max))
    db.commit()
    logger.debug("downsample_daily: %d rows", len(rows))


def purge_old_metrics(db: Session) -> None:
    """Supprime les métriques brutes > 7j et horaires > 3 mois."""
    raw_cutoff = datetime.now(timezone.utc) - timedelta(days=RAW_RETENTION_DAYS)
    hourly_cutoff = datetime.now(timezone.utc) - timedelta(days=HOURLY_RETENTION_DAYS)
    deleted_raw = db.query(Metric).filter(Metric.timestamp < raw_cutoff).delete()
    deleted_hourly = db.query(MetricHourly).filter(MetricHourly.hour < hourly_cutoff).delete()
    db.commit()
    logger.info("Purged %d raw, %d hourly metrics", deleted_raw, deleted_hourly)


def run_retention_job(db: Session) -> None:
    downsample_hourly(db)
    downsample_daily(db)
    purge_old_metrics(db)
```

- [ ] **Step 5.4 : Lancer les tests**

```bash
pytest tests/test_retention.py -v
```
Attendu : 4 tests PASS

- [ ] **Step 5.5 : Commit**

```bash
git add backend/modules/retention.py tests/test_retention.py
git commit -m "feat: SQLite retention — hourly/daily downsampling and auto-purge"
```

---

## Task 6 : WebSocket Manager + APScheduler + FastAPI main

**Files:**
- Create: `backend/ws/__init__.py`
- Create: `backend/ws/manager.py`
- Create: `backend/scheduler.py`
- Create: `backend/api/__init__.py`
- Create: `backend/main.py`
- Create: `backend/modules/alert_engine.py`
- Create: `tests/test_ws_manager.py`

- [ ] **Step 6.1 : Écrire les tests WebSocket échouants**

Créer `tests/test_ws_manager.py` :

```python
import pytest
from unittest.mock import AsyncMock
from backend.ws.manager import WebSocketManager


@pytest.mark.asyncio
async def test_connect_and_broadcast():
    manager = WebSocketManager()
    ws = AsyncMock()
    await manager.connect(ws)
    assert ws in manager.active_connections
    await manager.broadcast({"type": "metrics_update", "data": {"cpu": 23}})
    ws.send_json.assert_called_once_with({"type": "metrics_update", "data": {"cpu": 23}})


@pytest.mark.asyncio
async def test_disconnect_removes_client():
    manager = WebSocketManager()
    ws = AsyncMock()
    await manager.connect(ws)
    manager.disconnect(ws)
    assert ws not in manager.active_connections


@pytest.mark.asyncio
async def test_broadcast_skips_failed_clients():
    manager = WebSocketManager()
    good_ws = AsyncMock()
    bad_ws = AsyncMock()
    bad_ws.send_json = AsyncMock(side_effect=Exception("disconnected"))
    await manager.connect(good_ws)
    await manager.connect(bad_ws)
    await manager.broadcast({"type": "ping"})  # ne doit pas lever d'exception
    good_ws.send_json.assert_called_once()
```

- [ ] **Step 6.2 : Lancer pour vérifier l'échec**

```bash
pytest tests/test_ws_manager.py -v
```
Attendu : `ImportError`

- [ ] **Step 6.3 : Créer `backend/ws/__init__.py`** (vide)

- [ ] **Step 6.4 : Créer `backend/ws/manager.py`**

```python
import logging
from typing import Any
from fastapi import WebSocket

logger = logging.getLogger(__name__)


class WebSocketManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict[str, Any]) -> None:
        dead = []
        for ws in self.active_connections:
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)


ws_manager = WebSocketManager()
```

- [ ] **Step 6.5 : Lancer les tests WebSocket**

```bash
pytest tests/test_ws_manager.py -v
```
Attendu : 3 tests PASS

- [ ] **Step 6.6 : Créer `backend/modules/alert_engine.py`**

```python
async def send_alert(level: str, message: str, context: dict) -> None:
    """Stub v2 — sera implémenté avec Telegram/Email/Webhook."""
    pass
```

- [ ] **Step 6.7 : Créer `backend/api/__init__.py`**

```python
from fastapi import APIRouter

api_router = APIRouter(prefix="/api/v1")
```

- [ ] **Step 6.8 : Créer `backend/scheduler.py`**

```python
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

logger = logging.getLogger(__name__)
scheduler = AsyncIOScheduler()


def setup_scheduler(settings, db_factory, unraid_monitor, nmap_scanner, retention_job, ws_manager):
    async def collect_metrics():
        db = db_factory()
        try:
            await unraid_monitor.collect(db)
            from backend.models import Metric
            from sqlalchemy import desc
            latest: dict[str, float] = {}
            for m in db.query(Metric).order_by(desc(Metric.timestamp)).limit(20).all():
                if m.type not in latest:
                    latest[m.type] = m.value
            await ws_manager.broadcast({"type": "metrics_update", "data": latest})
        finally:
            db.close()

    async def run_nmap():
        db = db_factory()
        try:
            nmap_scanner.scan(db)
        finally:
            db.close()

    async def run_retention():
        db = db_factory()
        try:
            retention_job(db)
        finally:
            db.close()

    scheduler.add_job(
        collect_metrics, IntervalTrigger(seconds=settings.metrics_interval), id="collect_metrics"
    )
    scheduler.add_job(
        run_nmap, IntervalTrigger(seconds=settings.nmap_interval), id="nmap_scan"
    )
    scheduler.add_job(
        run_retention, IntervalTrigger(hours=1), id="retention"
    )
```

- [ ] **Step 6.9 : Créer `backend/main.py`**

```python
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from backend.config import settings
from backend.database import init_db, SessionLocal
from backend.modules.unraid_monitor import UnraidMonitor
from backend.modules.nmap_scanner import NmapScanner
from backend.modules.retention import run_retention_job
from backend.ws.manager import ws_manager
from backend.scheduler import scheduler, setup_scheduler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

FRONTEND_DIR = Path(__file__).parent.parent / "frontend" / "dist"


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not settings.testing:
        init_db()
        # Seed config par défaut si vide
        from backend.models import ConfigEntry
        db = SessionLocal()
        if not db.query(ConfigEntry).first():
            defaults = {
                "nmap_range": settings.nmap_range,
                "nmap_interval": str(settings.nmap_interval),
                "metrics_interval": str(settings.metrics_interval),
                "UNRAID_HOST": settings.unraid_host,
                "UNRAID_API_PORT": str(settings.unraid_api_port),
            }
            for k, v in defaults.items():
                db.add(ConfigEntry(key=k, value=v))
            db.commit()
        db.close()

        monitor = UnraidMonitor(
            host=settings.unraid_host,
            api_key=settings.unraid_api_key,
            api_port=settings.unraid_api_port,
        )
        scanner = NmapScanner(network_range=settings.nmap_range)
        setup_scheduler(settings, SessionLocal, monitor, scanner, run_retention_job, ws_manager)
        scheduler.start()
        logger.info("lach-sentinel started — monitoring %s", settings.unraid_host)

    yield

    if not settings.testing and scheduler.running:
        scheduler.shutdown()


app = FastAPI(title="lach-sentinel", lifespan=lifespan)

from backend.api import api_router  # noqa: E402
app.include_router(api_router)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)


if FRONTEND_DIR.exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIR / "assets"), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa_fallback(full_path: str):
        return FileResponse(FRONTEND_DIR / "index.html")
```

- [ ] **Step 6.10 : Lancer tous les tests backend jusqu'ici**

```bash
pytest tests/ -v
```
Attendu : tous les tests PASS

- [ ] **Step 6.11 : Commit**

```bash
git add backend/ws/ backend/scheduler.py backend/api/__init__.py backend/main.py backend/modules/alert_engine.py tests/test_ws_manager.py
git commit -m "feat: WebSocket manager, APScheduler, FastAPI app entry point"
```

---

## Task 7 : API REST — métriques, conteneurs, VMs

**Files:**
- Create: `backend/api/metrics.py`
- Create: `backend/api/containers.py`
- Create: `backend/api/vms.py`
- Modify: `backend/api/__init__.py`
- Create: `tests/test_api_metrics.py`

- [ ] **Step 7.1 : Écrire les tests échouants**

Créer `tests/test_api_metrics.py` :

```python
import pytest
import os
os.environ["TESTING"] = "true"

from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.main import app
from backend.database import Base, get_db
from backend.models import Metric


@pytest.fixture
def client():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
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
```

- [ ] **Step 7.2 : Lancer pour vérifier l'échec**

```bash
pytest tests/test_api_metrics.py -v
```
Attendu : échec (routes pas encore enregistrées)

- [ ] **Step 7.3 : Créer `backend/api/metrics.py`**

```python
from datetime import datetime, timezone, timedelta
from typing import Literal
from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Metric, MetricHourly, MetricDaily

router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get("/current")
def get_current_metrics(db: Session = Depends(get_db)) -> dict:
    latest: dict[str, float] = {}
    for row in db.query(Metric).order_by(desc(Metric.timestamp)).limit(100).all():
        if row.type not in latest:
            latest[row.type] = row.value
    return latest


@router.get("/history")
def get_metrics_history(
    type: str = Query(...),
    resolution: Literal["raw", "hourly", "daily"] = Query("raw"),
    from_: datetime | None = Query(None, alias="from"),
    to: datetime | None = Query(None),
    db: Session = Depends(get_db),
) -> list[dict]:
    to = to or datetime.now(timezone.utc)
    from_ = from_ or (to - timedelta(hours=24))

    if resolution == "raw":
        rows = db.query(Metric).filter(
            Metric.type == type, Metric.timestamp >= from_, Metric.timestamp <= to
        ).order_by(Metric.timestamp).all()
        return [{"timestamp": r.timestamp.isoformat(), "value": r.value} for r in rows]

    if resolution == "hourly":
        rows = db.query(MetricHourly).filter(
            MetricHourly.type == type, MetricHourly.hour >= from_, MetricHourly.hour <= to
        ).order_by(MetricHourly.hour).all()
        return [{"timestamp": r.hour.isoformat(), "avg": r.avg, "min": r.min, "max": r.max} for r in rows]

    rows = db.query(MetricDaily).filter(
        MetricDaily.type == type,
        MetricDaily.day >= from_.date(),
        MetricDaily.day <= to.date(),
    ).order_by(MetricDaily.day).all()
    return [{"timestamp": r.day.isoformat(), "avg": r.avg, "min": r.min, "max": r.max} for r in rows]
```

- [ ] **Step 7.4 : Créer `backend/api/containers.py`**

```python
import json
from fastapi import APIRouter, Depends
from sqlalchemy import desc
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Metric

router = APIRouter(prefix="/containers", tags=["containers"])


@router.get("")
def get_containers(db: Session = Depends(get_db)) -> list[dict]:
    row = db.query(Metric).filter(
        Metric.type == "containers", Metric.meta.isnot(None)
    ).order_by(desc(Metric.timestamp)).first()
    return json.loads(row.meta) if row else []
```

- [ ] **Step 7.5 : Créer `backend/api/vms.py`**

```python
import json
from fastapi import APIRouter, Depends
from sqlalchemy import desc
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Metric

router = APIRouter(prefix="/vms", tags=["vms"])


@router.get("")
def get_vms(db: Session = Depends(get_db)) -> list[dict]:
    row = db.query(Metric).filter(
        Metric.type == "vms", Metric.meta.isnot(None)
    ).order_by(desc(Metric.timestamp)).first()
    return json.loads(row.meta) if row else []
```

- [ ] **Step 7.6 : Mettre à jour `backend/api/__init__.py`**

```python
from fastapi import APIRouter
from backend.api.metrics import router as metrics_router
from backend.api.containers import router as containers_router
from backend.api.vms import router as vms_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(metrics_router)
api_router.include_router(containers_router)
api_router.include_router(vms_router)
```

- [ ] **Step 7.7 : Lancer les tests**

```bash
pytest tests/test_api_metrics.py -v
```
Attendu : 3 tests PASS

- [ ] **Step 7.8 : Commit**

```bash
git add backend/api/metrics.py backend/api/containers.py backend/api/vms.py backend/api/__init__.py tests/test_api_metrics.py
git commit -m "feat: REST API — metrics/current, metrics/history, containers, VMs"
```

---

## Task 8 : API REST — hôtes & services

**Files:**
- Create: `backend/api/hosts.py`
- Modify: `backend/api/__init__.py`
- Create: `tests/test_api_hosts.py`

- [ ] **Step 8.1 : Écrire les tests échouants**

Créer `tests/test_api_hosts.py` :

```python
import pytest
import os
os.environ["TESTING"] = "true"

from datetime import datetime, timezone
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.main import app
from backend.database import Base, get_db
from backend.models import Host


@pytest.fixture
def client():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
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
```

- [ ] **Step 8.2 : Lancer pour vérifier l'échec**

```bash
pytest tests/test_api_hosts.py -v
```
Attendu : échec (routes pas encore enregistrées)

- [ ] **Step 8.3 : Créer `backend/api/hosts.py`**

```python
import json
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Host, Service

router = APIRouter(prefix="/hosts", tags=["hosts"])


class HostUpdate(BaseModel):
    label: str | None = None
    notes: str | None = None
    tags: list[str] | None = None
    monitoring_enabled: bool | None = None
    os: str | None = None


def host_to_dict(h: Host) -> dict:
    return {
        "id": h.id,
        "ip": h.ip,
        "hostname": h.hostname,
        "mac": h.mac,
        "vendor": h.vendor,
        "os": h.os,
        "status": h.status,
        "label": h.label,
        "notes": h.notes,
        "tags": json.loads(h.tags) if h.tags else [],
        "monitoring_enabled": h.monitoring_enabled,
        "first_seen": h.first_seen.isoformat(),
        "last_seen": h.last_seen.isoformat(),
    }


@router.get("")
def list_hosts(db: Session = Depends(get_db)) -> list[dict]:
    return [host_to_dict(h) for h in db.query(Host).order_by(Host.ip).all()]


@router.get("/{host_id}")
def get_host(host_id: int, db: Session = Depends(get_db)) -> dict:
    h = db.query(Host).filter_by(id=host_id).first()
    if not h:
        raise HTTPException(status_code=404, detail="Host not found")
    return host_to_dict(h)


@router.put("/{host_id}")
def update_host(host_id: int, body: HostUpdate, db: Session = Depends(get_db)) -> dict:
    h = db.query(Host).filter_by(id=host_id).first()
    if not h:
        raise HTTPException(status_code=404, detail="Host not found")
    if body.label is not None:
        h.label = body.label
    if body.notes is not None:
        h.notes = body.notes
    if body.tags is not None:
        h.tags = json.dumps(body.tags)
    if body.monitoring_enabled is not None:
        h.monitoring_enabled = body.monitoring_enabled
    if body.os is not None:
        h.os = body.os
    db.commit()
    db.refresh(h)
    return host_to_dict(h)


@router.delete("/{host_id}", status_code=204)
def delete_host(host_id: int, db: Session = Depends(get_db)) -> None:
    h = db.query(Host).filter_by(id=host_id).first()
    if not h:
        raise HTTPException(status_code=404, detail="Host not found")
    db.delete(h)
    db.commit()


@router.get("/{host_id}/services")
def list_services(host_id: int, db: Session = Depends(get_db)) -> list[dict]:
    h = db.query(Host).filter_by(id=host_id).first()
    if not h:
        raise HTTPException(status_code=404, detail="Host not found")
    return [
        {
            "id": s.id,
            "port": s.port,
            "protocol": s.protocol,
            "service_name": s.service_name,
            "version": s.version,
            "state": s.state,
            "last_seen": s.last_seen.isoformat() if s.last_seen else None,
        }
        for s in h.services
    ]
```

- [ ] **Step 8.4 : Mettre à jour `backend/api/__init__.py`**

```python
from fastapi import APIRouter
from backend.api.metrics import router as metrics_router
from backend.api.containers import router as containers_router
from backend.api.vms import router as vms_router
from backend.api.hosts import router as hosts_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(metrics_router)
api_router.include_router(containers_router)
api_router.include_router(vms_router)
api_router.include_router(hosts_router)
```

- [ ] **Step 8.5 : Lancer les tests**

```bash
pytest tests/test_api_hosts.py -v
```
Attendu : 6 tests PASS

- [ ] **Step 8.6 : Commit**

```bash
git add backend/api/hosts.py backend/api/__init__.py tests/test_api_hosts.py
git commit -m "feat: REST API — hosts CRUD, tags, notes, services"
```

---

## Task 9 : API REST — scans & config

**Files:**
- Create: `backend/api/scans.py`
- Create: `backend/api/config_api.py`
- Modify: `backend/api/__init__.py`
- Create: `tests/test_api_scans.py`

- [ ] **Step 9.1 : Écrire les tests échouants**

Créer `tests/test_api_scans.py` :

```python
import pytest
import os
os.environ["TESTING"] = "true"

from datetime import datetime, timezone
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.main import app
from backend.database import Base, get_db
from backend.models import ScanResult, ConfigEntry


@pytest.fixture
def client():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
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
```

- [ ] **Step 9.2 : Lancer pour vérifier l'échec**

```bash
pytest tests/test_api_scans.py -v
```
Attendu : échec (routes pas encore enregistrées)

- [ ] **Step 9.3 : Créer `backend/api/scans.py`**

```python
from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import ScanResult
from backend.config import settings

router = APIRouter(prefix="/scans", tags=["scans"])


def scan_to_dict(s: ScanResult) -> dict:
    return {
        "id": s.id,
        "started_at": s.started_at.isoformat(),
        "finished_at": s.finished_at.isoformat() if s.finished_at else None,
        "range": s.range,
        "hosts_found": s.hosts_found,
        "status": s.status,
    }


@router.get("")
def list_scans(limit: int = 20, db: Session = Depends(get_db)) -> list[dict]:
    rows = db.query(ScanResult).order_by(ScanResult.started_at.desc()).limit(limit).all()
    return [scan_to_dict(r) for r in rows]


@router.post("/trigger", status_code=202)
def trigger_scan(background_tasks: BackgroundTasks, db: Session = Depends(get_db)) -> dict:
    from backend.modules.nmap_scanner import NmapScanner
    scanner = NmapScanner(network_range=settings.nmap_range)
    background_tasks.add_task(scanner.scan, db)
    return {"status": "scan_triggered", "range": settings.nmap_range}
```

- [ ] **Step 9.4 : Créer `backend/api/config_api.py`**

```python
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
```

- [ ] **Step 9.5 : Mettre à jour `backend/api/__init__.py`**

```python
from fastapi import APIRouter
from backend.api.metrics import router as metrics_router
from backend.api.containers import router as containers_router
from backend.api.vms import router as vms_router
from backend.api.hosts import router as hosts_router
from backend.api.scans import router as scans_router
from backend.api.config_api import router as config_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(metrics_router)
api_router.include_router(containers_router)
api_router.include_router(vms_router)
api_router.include_router(hosts_router)
api_router.include_router(scans_router)
api_router.include_router(config_router)
```

- [ ] **Step 9.6 : Lancer la suite complète**

```bash
pytest tests/ -v
```
Attendu : tous les tests PASS

- [ ] **Step 9.7 : Commit**

```bash
git add backend/api/scans.py backend/api/config_api.py backend/api/__init__.py tests/test_api_scans.py
git commit -m "feat: REST API — scans history, scan trigger, config CRUD"
```

---

## Task 10 : Frontend Vue.js — setup, router, stores, layout

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/tsconfig.json`
- Create: `frontend/index.html`
- Create: `frontend/src/main.ts`
- Create: `frontend/src/App.vue`
- Create: `frontend/src/router/index.ts`
- Create: `frontend/src/stores/ws.ts`
- Create: `frontend/src/stores/metrics.ts`
- Create: `frontend/src/stores/hosts.ts`
- Create: `frontend/src/components/layout/AppLayout.vue`
- Create: `frontend/src/components/layout/Sidebar.vue`

- [ ] **Step 10.1 : Créer `frontend/package.json`**

```json
{
  "name": "lach-sentinel-ui",
  "version": "0.1.0",
  "private": true,
  "scripts": {
    "dev": "vite",
    "build": "vue-tsc && vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "vue": "^3.4.0",
    "vue-router": "^4.3.0",
    "pinia": "^2.1.0",
    "chart.js": "^4.4.0",
    "vue-chartjs": "^5.3.0"
  },
  "devDependencies": {
    "@vitejs/plugin-vue": "^5.0.0",
    "typescript": "^5.3.0",
    "vite": "^5.2.0",
    "vue-tsc": "^2.0.0"
  }
}
```

- [ ] **Step 10.2 : Créer `frontend/vite.config.ts`**

```typescript
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    proxy: {
      '/api': 'http://localhost:8888',
      '/ws': { target: 'ws://localhost:8888', ws: true },
    }
  },
  build: { outDir: 'dist' }
})
```

- [ ] **Step 10.3 : Créer `frontend/tsconfig.json`**

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "module": "ESNext",
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "preserve",
    "strict": true
  },
  "include": ["src/**/*.ts", "src/**/*.d.ts", "src/**/*.tsx", "src/**/*.vue"]
}
```

- [ ] **Step 10.4 : Créer `frontend/index.html`**

```html
<!DOCTYPE html>
<html lang="fr">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>lach-sentinel</title>
  </head>
  <body>
    <div id="app"></div>
    <script type="module" src="/src/main.ts"></script>
  </body>
</html>
```

- [ ] **Step 10.5 : Créer `frontend/src/main.ts`**

```typescript
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'

createApp(App).use(createPinia()).use(router).mount('#app')
```

- [ ] **Step 10.6 : Créer `frontend/src/App.vue`**

```vue
<template>
  <AppLayout />
</template>

<script setup lang="ts">
import AppLayout from './components/layout/AppLayout.vue'
import { useWsStore } from './stores/ws'
import { onMounted } from 'vue'

const wsStore = useWsStore()
onMounted(() => wsStore.connect())
</script>
```

- [ ] **Step 10.7 : Créer `frontend/src/router/index.ts`**

```typescript
import { createRouter, createWebHistory } from 'vue-router'
import Dashboard from '../views/Dashboard.vue'

export default createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', component: Dashboard },
    { path: '/unraid', component: () => import('../views/UnraidView.vue') },
    { path: '/containers', component: () => import('../views/ContainersView.vue') },
    { path: '/vms', component: () => import('../views/VmsView.vue') },
    { path: '/network', component: () => import('../views/NetworkView.vue') },
    { path: '/hosts', component: () => import('../views/HostsView.vue') },
    { path: '/scans', component: () => import('../views/ScansView.vue') },
    { path: '/settings', component: () => import('../views/SettingsView.vue') },
  ]
})
```

- [ ] **Step 10.8 : Créer `frontend/src/stores/metrics.ts`**

```typescript
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

interface CurrentMetrics {
  cpu?: number
  ram_used_gb?: number
  ram_total_gb?: number
  temp_cpu?: number
  uptime_seconds?: number
  array_used_tb?: number
  array_total_tb?: number
  [key: string]: number | undefined
}

export const useMetricsStore = defineStore('metrics', () => {
  const current = ref<CurrentMetrics>({})

  async function fetchCurrent() {
    const resp = await fetch('/api/v1/metrics/current')
    if (resp.ok) current.value = await resp.json()
  }

  function updateCurrent(data: CurrentMetrics) {
    current.value = { ...current.value, ...data }
  }

  const uptimeFormatted = computed(() => {
    const s = current.value.uptime_seconds ?? 0
    const days = Math.floor(s / 86400)
    const hours = Math.floor((s % 86400) / 3600)
    return `${days}j ${hours}h`
  })

  return { current, fetchCurrent, updateCurrent, uptimeFormatted }
})
```

- [ ] **Step 10.9 : Créer `frontend/src/stores/ws.ts`**

```typescript
import { defineStore } from 'pinia'
import { ref } from 'vue'
import { useMetricsStore } from './metrics'

export const useWsStore = defineStore('ws', () => {
  const connected = ref(false)
  let retryDelay = 1000

  function connect() {
    const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws'
    const socket = new WebSocket(`${protocol}://${window.location.host}/ws`)

    socket.onopen = () => { connected.value = true; retryDelay = 1000 }

    socket.onmessage = (event) => {
      const msg = JSON.parse(event.data)
      if (msg.type === 'metrics_update') {
        useMetricsStore().updateCurrent(msg.data)
      }
    }

    socket.onclose = () => {
      connected.value = false
      setTimeout(() => { retryDelay = Math.min(retryDelay * 2, 30000); connect() }, retryDelay)
    }

    socket.onerror = () => socket.close()
  }

  return { connected, connect }
})
```

- [ ] **Step 10.10 : Créer `frontend/src/stores/hosts.ts`**

```typescript
import { defineStore } from 'pinia'
import { ref } from 'vue'

export interface Host {
  id: number
  ip: string
  hostname: string | null
  mac: string | null
  vendor: string | null
  os: string | null
  status: string
  label: string | null
  notes: string | null
  tags: string[]
  monitoring_enabled: boolean
  first_seen: string
  last_seen: string
}

export const useHostsStore = defineStore('hosts', () => {
  const hosts = ref<Host[]>([])
  const loading = ref(false)

  async function fetchHosts() {
    loading.value = true
    const resp = await fetch('/api/v1/hosts')
    if (resp.ok) hosts.value = await resp.json()
    loading.value = false
  }

  async function updateHost(id: number, updates: Partial<Host>) {
    const resp = await fetch(`/api/v1/hosts/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(updates),
    })
    if (resp.ok) {
      const updated = await resp.json()
      const idx = hosts.value.findIndex(h => h.id === id)
      if (idx !== -1) hosts.value[idx] = updated
    }
  }

  async function deleteHost(id: number) {
    await fetch(`/api/v1/hosts/${id}`, { method: 'DELETE' })
    hosts.value = hosts.value.filter(h => h.id !== id)
  }

  return { hosts, loading, fetchHosts, updateHost, deleteHost }
})
```

- [ ] **Step 10.11 : Créer `frontend/src/components/layout/Sidebar.vue`**

```vue
<template>
  <aside class="sidebar">
    <div class="sidebar-header">
      <div class="logo-icon"></div>
      <div>
        <span class="logo-name">lach-sentinel</span>
        <span class="logo-status" :class="{ online: ws.connected }">
          {{ ws.connected ? '● En ligne' : '○ Déconnecté' }}
        </span>
      </div>
    </div>
    <nav class="sidebar-nav">
      <router-link to="/" class="nav-item">Dashboard</router-link>
      <router-link to="/unraid" class="nav-item">Unraid</router-link>
      <router-link to="/containers" class="nav-item">Conteneurs</router-link>
      <router-link to="/vms" class="nav-item">VMs</router-link>
      <div class="nav-divider"></div>
      <router-link to="/network" class="nav-item">Réseau</router-link>
      <router-link to="/hosts" class="nav-item">Hôtes</router-link>
      <router-link to="/scans" class="nav-item">Scans Nmap</router-link>
      <div class="nav-divider"></div>
      <router-link to="/settings" class="nav-item">Paramètres</router-link>
    </nav>
    <div class="sidebar-footer">192.168.111.253</div>
  </aside>
</template>

<script setup lang="ts">
import { useWsStore } from '../../stores/ws'
const ws = useWsStore()
</script>

<style scoped>
.sidebar { width:200px;background:#010409;border-right:1px solid #21262d;display:flex;flex-direction:column;height:100vh;position:fixed;left:0;top:0; }
.sidebar-header { display:flex;align-items:center;gap:10px;padding:16px 14px;border-bottom:1px solid #21262d; }
.logo-icon { width:28px;height:28px;background:linear-gradient(135deg,#4f8ef7,#7c3aed);border-radius:6px;flex-shrink:0; }
.logo-name { display:block;font-weight:700;color:#fff;font-size:13px; }
.logo-status { display:block;font-size:10px;color:#6e7681; }
.logo-status.online { color:#4f8ef7; }
.sidebar-nav { padding:8px 0;flex:1; }
.nav-item { display:block;padding:8px 14px;color:#8b949e;text-decoration:none;font-size:14px; }
.nav-item:hover { color:#fff; }
.nav-item.router-link-active { color:#4f8ef7;background:rgba(79,142,247,0.1);border-right:2px solid #4f8ef7;font-weight:600; }
.nav-divider { height:1px;background:#21262d;margin:6px 0; }
.sidebar-footer { padding:10px 14px;border-top:1px solid #21262d;color:#6e7681;font-size:11px; }
</style>
```

- [ ] **Step 10.12 : Créer `frontend/src/components/layout/AppLayout.vue`**

```vue
<template>
  <div class="app-layout">
    <Sidebar />
    <main class="main-content">
      <router-view />
    </main>
  </div>
</template>

<script setup lang="ts">
import Sidebar from './Sidebar.vue'
</script>

<style>
* { box-sizing: border-box; margin: 0; padding: 0; }
body { background: #0d1117; color: #e6edf3; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; }
</style>

<style scoped>
.app-layout { display:flex;min-height:100vh; }
.main-content { margin-left:200px;flex:1;padding:24px;overflow-y:auto; }
</style>
```

- [ ] **Step 10.13 : Installer les dépendances et vérifier le build**

```bash
cd frontend && npm install && npm run build && cd ..
```
Attendu : dossier `dist/` créé sans erreur TypeScript

- [ ] **Step 10.14 : Commit**

```bash
git add frontend/
git commit -m "feat: Vue.js setup — router, Pinia stores, layout sidebar"
```

---

## Task 11 : Dashboard + widgets

**Files:**
- Create: `frontend/src/components/widgets/KpiCard.vue`
- Create: `frontend/src/components/widgets/StorageWidget.vue`
- Create: `frontend/src/components/widgets/ContainersWidget.vue`
- Create: `frontend/src/components/widgets/VmsWidget.vue`
- Create: `frontend/src/components/widgets/NetworkWidget.vue`
- Create: `frontend/src/views/Dashboard.vue`

- [ ] **Step 11.1 : Créer `frontend/src/components/widgets/KpiCard.vue`**

```vue
<template>
  <div class="kpi-card">
    <div class="label">{{ label }}</div>
    <div class="value">{{ value }}</div>
    <div class="bar" v-if="percent !== undefined">
      <div class="bar-fill" :style="{ width: clamp(percent) + '%', background: color }"></div>
    </div>
    <div class="sub" v-if="sub">{{ sub }}</div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
const props = defineProps<{ label: string; value: string | number; percent?: number; sub?: string; warn?: number; danger?: number }>()
const clamp = (v: number) => Math.min(Math.max(v, 0), 100)
const color = computed(() => {
  if (props.percent === undefined) return '#4f8ef7'
  if (props.danger !== undefined && props.percent >= props.danger) return '#f85149'
  if (props.warn !== undefined && props.percent >= props.warn) return '#ffc107'
  return '#4f8ef7'
})
</script>

<style scoped>
.kpi-card { background:#161b22;border:1px solid #30363d;border-radius:8px;padding:14px; }
.label { color:#6e7681;font-size:11px;margin-bottom:4px; }
.value { font-size:22px;font-weight:700;color:#e6edf3; }
.bar { height:4px;background:#21262d;border-radius:2px;margin-top:8px; }
.bar-fill { height:4px;border-radius:2px;transition:width .3s; }
.sub { font-size:11px;color:#6e7681;margin-top:4px; }
</style>
```

- [ ] **Step 11.2 : Créer `frontend/src/components/widgets/StorageWidget.vue`**

```vue
<template>
  <div class="widget">
    <h3>Stockage</h3>
    <div class="row"><span class="lbl">Array</span>
      <div class="bar"><div class="fill" :style="{width:arrayPct+'%'}"></div></div>
      <span class="val">{{ m.current.array_used_tb?.toFixed(1) }}TB / {{ m.current.array_total_tb?.toFixed(1) }}TB</span>
    </div>
    <div class="meta"><span>Parité</span><span class="ok">✓ OK</span></div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useMetricsStore } from '../../stores/metrics'
const m = useMetricsStore()
const arrayPct = computed(() => {
  const t = m.current.array_total_tb ?? 0
  return t > 0 ? Math.round((m.current.array_used_tb ?? 0) / t * 100) : 0
})
</script>

<style scoped>
.widget { background:#161b22;border:1px solid #30363d;border-radius:8px;padding:14px; }
h3 { font-size:13px;font-weight:600;color:#e6edf3;margin:0 0 12px; }
.row { display:flex;align-items:center;gap:8px;margin-bottom:8px; }
.lbl { color:#6e7681;font-size:12px;width:50px;flex-shrink:0; }
.bar { flex:1;height:6px;background:#21262d;border-radius:3px; }
.fill { height:6px;background:#4f8ef7;border-radius:3px;transition:width .3s; }
.val { color:#e6edf3;font-size:11px;width:100px;text-align:right; }
.meta { display:flex;justify-content:space-between;font-size:11px;color:#6e7681;margin-top:4px; }
.ok { color:#42b883; }
</style>
```

- [ ] **Step 11.3 : Créer `frontend/src/components/widgets/ContainersWidget.vue`**

```vue
<template>
  <div class="widget">
    <h3>Conteneurs Docker <span class="count">({{ containers.length }})</span></h3>
    <div v-for="c in containers.slice(0,5)" :key="c.name" class="row">
      <span class="dot" :class="c.status"></span>
      <span class="name">{{ c.name }}</span>
      <span class="meta">{{ c.status === 'running' ? fmtMem(c.stats?.memory) : 'Arrêté' }}</span>
    </div>
    <div v-if="containers.length > 5" class="more">
      + {{ containers.length - 5 }} autres · <router-link to="/containers">Voir tout →</router-link>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
const containers = ref<any[]>([])
const fmtMem = (b?: number) => b ? (b/1024/1024).toFixed(0)+' MB' : ''
onMounted(async () => { const r = await fetch('/api/v1/containers'); if (r.ok) containers.value = await r.json() })
</script>

<style scoped>
.widget { background:#161b22;border:1px solid #30363d;border-radius:8px;padding:14px; }
h3 { font-size:13px;font-weight:600;color:#e6edf3;margin:0 0 12px; }
.count { font-weight:400;color:#6e7681; }
.row { display:flex;align-items:center;gap:8px;margin-bottom:6px;font-size:13px; }
.dot { width:7px;height:7px;border-radius:50%;flex-shrink:0; }
.dot.running { background:#42b883; } .dot.stopped,.dot.exited { background:#f85149; }
.name { flex:1;color:#e6edf3; }
.meta { color:#6e7681;font-size:11px; }
.more { font-size:11px;color:#6e7681;margin-top:4px; }
.more a { color:#4f8ef7;text-decoration:none; }
</style>
```

- [ ] **Step 11.4 : Créer `frontend/src/components/widgets/VmsWidget.vue`**

```vue
<template>
  <div class="widget">
    <h3>Machines Virtuelles <span class="count">({{ vms.length }})</span></h3>
    <div v-for="vm in vms" :key="vm.name" class="row">
      <span class="dot" :class="vm.status"></span>
      <span class="name">{{ vm.name }}</span>
      <span class="meta">{{ vm.status === 'running' ? `${vm.vcpus} vCPU · ${fmtMem(vm.memory)}` : 'Éteinte' }}</span>
    </div>
    <div v-if="!vms.length" class="empty">Aucune VM</div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
const vms = ref<any[]>([])
const fmtMem = (b?: number) => b ? (b/1024/1024/1024).toFixed(0)+' GB' : ''
onMounted(async () => { const r = await fetch('/api/v1/vms'); if (r.ok) vms.value = await r.json() })
</script>

<style scoped>
.widget { background:#161b22;border:1px solid #30363d;border-radius:8px;padding:14px; }
h3 { font-size:13px;font-weight:600;color:#e6edf3;margin:0 0 12px; }
.count { font-weight:400;color:#6e7681; }
.row { display:flex;align-items:center;gap:8px;margin-bottom:6px;font-size:13px; }
.dot { width:7px;height:7px;border-radius:50%;flex-shrink:0; }
.dot.running { background:#42b883; } .dot.stopped,.dot.shutoff { background:#6e7681; }
.name { flex:1;color:#e6edf3; }
.meta { color:#6e7681;font-size:11px; }
.empty { color:#6e7681;font-size:13px; }
</style>
```

- [ ] **Step 11.5 : Créer `frontend/src/components/widgets/NetworkWidget.vue`**

```vue
<template>
  <div class="widget">
    <div class="header">
      <h3>Réseau local</h3>
      <span class="badge" v-if="lastScan">Scan il y a {{ timeSince(lastScan.finished_at) }}</span>
    </div>
    <div class="stats">
      <div class="stat"><div class="val blue">{{ active }}</div><div class="lbl">Actifs</div></div>
      <div class="stat"><div class="val yellow">{{ newHosts }}</div><div class="lbl">Nouveaux</div></div>
      <div class="stat"><div class="val red">{{ absent }}</div><div class="lbl">Disparus</div></div>
    </div>
    <div class="footer">{{ range }} · <router-link to="/hosts">Voir les hôtes →</router-link></div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useHostsStore } from '../../stores/hosts'
const hosts = useHostsStore()
const lastScan = ref<any>(null)
const range = ref('192.168.111.0/24')
const active = computed(() => hosts.hosts.filter(h => h.status === 'active').length)
const absent = computed(() => hosts.hosts.filter(h => h.status === 'absent').length)
const newHosts = computed(() => hosts.hosts.filter(h => Date.now() - new Date(h.first_seen).getTime() < 86400000).length)
const timeSince = (iso: string) => { const m = Math.floor((Date.now()-new Date(iso).getTime())/60000); return m<60?`${m}min`:`${Math.floor(m/60)}h` }
onMounted(async () => {
  await hosts.fetchHosts()
  const r = await fetch('/api/v1/scans?limit=1'); if (r.ok) { const s = await r.json(); if (s.length) lastScan.value = s[0] }
  const c = await fetch('/api/v1/config'); if (c.ok) { const cfg = await c.json(); if (cfg.nmap_range) range.value = cfg.nmap_range }
})
</script>

<style scoped>
.widget { background:#161b22;border:1px solid #30363d;border-radius:8px;padding:14px; }
.header { display:flex;justify-content:space-between;align-items:center;margin-bottom:12px; }
h3 { font-size:13px;font-weight:600;color:#e6edf3;margin:0; }
.badge { font-size:10px;background:rgba(66,184,131,.15);color:#42b883;border-radius:4px;padding:2px 6px; }
.stats { display:flex;gap:16px;margin-bottom:10px; }
.stat { text-align:center; }
.val { font-size:24px;font-weight:700; }
.lbl { font-size:11px;color:#6e7681; }
.blue{color:#4f8ef7;} .yellow{color:#ffc107;} .red{color:#f85149;}
.footer { font-size:11px;color:#6e7681; }
.footer a { color:#4f8ef7;text-decoration:none; }
</style>
```

- [ ] **Step 11.6 : Créer `frontend/src/views/Dashboard.vue`**

```vue
<template>
  <div class="dashboard">
    <div class="dh">
      <h1>Vue d'ensemble</h1>
      <div class="dh-right">
        <span class="upd" v-if="m.current.cpu !== undefined">MàJ en direct</span>
        <button class="btn-sec" @click="show = !show">⚙ Widgets</button>
      </div>
    </div>

    <div class="kpi-grid" v-if="w.kpis">
      <KpiCard label="CPU" :value="(m.current.cpu??0).toFixed(1)+'%'" :percent="m.current.cpu" :warn="70" :danger="90" />
      <KpiCard label="RAM" :value="(m.current.ram_used_gb??0).toFixed(1)+' GB'" :percent="ramPct" :warn="80" :danger="90" />
      <KpiCard label="Temp. CPU" :value="(m.current.temp_cpu??0).toFixed(0)+'°C'" :percent="m.current.temp_cpu" :warn="70" :danger="85" />
      <KpiCard label="Uptime" :value="m.uptimeFormatted" />
    </div>

    <div class="two-col">
      <StorageWidget v-if="w.storage" />
      <ContainersWidget v-if="w.containers" />
    </div>
    <div class="two-col">
      <VmsWidget v-if="w.vms" />
      <NetworkWidget v-if="w.network" />
    </div>

    <div class="panel" v-if="show">
      <h3>Widgets visibles</h3>
      <label v-for="(_, key) in w" :key="key">
        <input type="checkbox" v-model="w[key]" @change="save" /> {{ labels[key] }}
      </label>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, reactive, onMounted } from 'vue'
import KpiCard from '../components/widgets/KpiCard.vue'
import StorageWidget from '../components/widgets/StorageWidget.vue'
import ContainersWidget from '../components/widgets/ContainersWidget.vue'
import VmsWidget from '../components/widgets/VmsWidget.vue'
import NetworkWidget from '../components/widgets/NetworkWidget.vue'
import { useMetricsStore } from '../stores/metrics'

const m = useMetricsStore()
const show = ref(false)
const labels: Record<string,string> = { kpis:'KPIs système', storage:'Stockage', containers:'Conteneurs', vms:'VMs', network:'Réseau' }
const saved = localStorage.getItem('sentinel-widgets')
const w = reactive<Record<string,boolean>>(saved ? JSON.parse(saved) : { kpis:true, storage:true, containers:true, vms:true, network:true })
const save = () => localStorage.setItem('sentinel-widgets', JSON.stringify(w))
const ramPct = computed(() => { const t = m.current.ram_total_gb??0; return t>0?Math.round((m.current.ram_used_gb??0)/t*100):0 })
onMounted(() => m.fetchCurrent())
</script>

<style scoped>
.dashboard { max-width:1200px; }
.dh { display:flex;justify-content:space-between;align-items:center;margin-bottom:20px; }
h1 { font-size:20px;font-weight:700;color:#e6edf3; }
.dh-right { display:flex;gap:12px;align-items:center; }
.upd { color:#6e7681;font-size:12px; }
.btn-sec { background:#21262d;border:1px solid #30363d;color:#8b949e;padding:6px 12px;border-radius:6px;cursor:pointer;font-size:13px; }
.kpi-grid { display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:12px; }
.two-col { display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:12px; }
.panel { background:#161b22;border:1px solid #30363d;border-radius:8px;padding:16px;margin-top:12px; }
.panel h3 { margin:0 0 12px;font-size:14px;color:#e6edf3; }
.panel label { display:flex;align-items:center;gap:8px;font-size:13px;color:#8b949e;margin-bottom:8px;cursor:pointer; }
</style>
```

- [ ] **Step 11.7 : Vérifier le build**

```bash
cd frontend && npm run build && cd ..
```
Attendu : build réussi sans erreur TypeScript

- [ ] **Step 11.8 : Commit**

```bash
git add frontend/src/
git commit -m "feat: Dashboard view with toggleable KPI and monitoring widgets"
```

---

## Task 12 : Vues Hôtes, Scans, Paramètres et vues secondaires

**Files:**
- Create: `frontend/src/components/hosts/HostEditModal.vue`
- Create: `frontend/src/components/hosts/HostTable.vue`
- Create: `frontend/src/views/HostsView.vue`
- Create: `frontend/src/views/ScansView.vue`
- Create: `frontend/src/views/SettingsView.vue`
- Create: `frontend/src/views/ContainersView.vue`
- Create: `frontend/src/views/VmsView.vue`
- Create: `frontend/src/views/NetworkView.vue`
- Create: `frontend/src/views/UnraidView.vue`

- [ ] **Step 12.1 : Créer `frontend/src/components/hosts/HostEditModal.vue`**

```vue
<template>
  <div class="overlay" @click.self="$emit('close')">
    <div class="modal">
      <h3>Éditer — {{ host.ip }}</h3>
      <div class="fg"><label>Nom personnalisé</label><input v-model="f.label" class="inp" /></div>
      <div class="fg"><label>Notes</label><textarea v-model="f.notes" class="inp" rows="3"></textarea></div>
      <div class="fg"><label>Tags (virgule)</label><input v-model="tagsRaw" class="inp" /></div>
      <div class="fg row"><label>Monitoring activé</label><input type="checkbox" v-model="f.monitoring_enabled" /></div>
      <div class="actions">
        <button class="btn-sec" @click="$emit('close')">Annuler</button>
        <button class="btn-pri" @click="save">Enregistrer</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useHostsStore } from '../../stores/hosts'
const props = defineProps<{ host: any }>()
const emit = defineEmits(['close'])
const store = useHostsStore()
const f = reactive({ label: props.host.label||'', notes: props.host.notes||'', monitoring_enabled: props.host.monitoring_enabled })
const tagsRaw = ref((props.host.tags||[]).join(', '))
async function save() {
  const tags = tagsRaw.value.split(',').map((t:string)=>t.trim()).filter(Boolean)
  await store.updateHost(props.host.id, { ...f, tags })
  emit('close')
}
</script>

<style scoped>
.overlay { position:fixed;inset:0;background:rgba(0,0,0,.6);display:flex;align-items:center;justify-content:center;z-index:100; }
.modal { background:#161b22;border:1px solid #30363d;border-radius:10px;padding:24px;width:480px;max-width:95vw; }
h3 { margin:0 0 20px;font-size:16px;color:#e6edf3; }
.fg { margin-bottom:16px; }
label { display:block;font-size:12px;color:#6e7681;margin-bottom:6px; }
.inp { width:100%;background:#0d1117;border:1px solid #30363d;border-radius:6px;padding:8px 12px;color:#e6edf3;font-size:14px; }
.row { display:flex;justify-content:space-between;align-items:center; }
.actions { display:flex;gap:10px;justify-content:flex-end;margin-top:20px; }
.btn-sec { background:#21262d;border:1px solid #30363d;color:#8b949e;padding:8px 16px;border-radius:6px;cursor:pointer; }
.btn-pri { background:#4f8ef7;border:none;color:#fff;padding:8px 16px;border-radius:6px;cursor:pointer;font-weight:600; }
</style>
```

- [ ] **Step 12.2 : Créer `frontend/src/components/hosts/HostTable.vue`**

```vue
<template>
  <div>
    <div class="toolbar">
      <input v-model="q" class="search" placeholder="Rechercher IP, nom, vendor…" />
      <span class="count">{{ filtered.length }} hôtes</span>
    </div>
    <table class="table">
      <thead><tr><th>Statut</th><th>IP</th><th>Nom / Label</th><th>MAC / Vendor</th><th>OS</th><th>Tags</th><th>Vu</th><th>Actions</th></tr></thead>
      <tbody>
        <tr v-for="h in filtered" :key="h.id" :class="{absent: h.status==='absent'}">
          <td><span class="dot" :class="h.status"></span></td>
          <td class="mono">{{ h.ip }}</td>
          <td>{{ h.label || h.hostname || '—' }}</td>
          <td class="small">{{ h.vendor ? `${h.vendor} (${h.mac})` : h.mac || '—' }}</td>
          <td>{{ h.os || '—' }}</td>
          <td><span v-for="t in h.tags" :key="t" class="tag">{{ t }}</span></td>
          <td class="small">{{ rel(h.last_seen) }}</td>
          <td>
            <button class="act" @click="editing=h">Éditer</button>
            <button class="act danger" @click="del(h)">Sup.</button>
          </td>
        </tr>
      </tbody>
    </table>
    <HostEditModal v-if="editing" :host="editing" @close="editing=null" />
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useHostsStore } from '../../stores/hosts'
import HostEditModal from './HostEditModal.vue'
const store = useHostsStore()
const q = ref('')
const editing = ref<any>(null)
const filtered = computed(() => {
  const s = q.value.toLowerCase()
  return store.hosts.filter(h => h.ip.includes(s)||(h.label||'').toLowerCase().includes(s)||(h.hostname||'').toLowerCase().includes(s)||(h.vendor||'').toLowerCase().includes(s))
})
const rel = (iso: string) => { const m=Math.floor((Date.now()-new Date(iso).getTime())/60000); if(m<1)return'à l\'instant'; if(m<60)return`il y a ${m}min`; if(m<1440)return`il y a ${Math.floor(m/60)}h`; return`il y a ${Math.floor(m/1440)}j` }
async function del(h: any) { if(confirm(`Supprimer ${h.ip} ?`)) await store.deleteHost(h.id) }
</script>

<style scoped>
.toolbar { display:flex;justify-content:space-between;align-items:center;margin-bottom:16px; }
.search { background:#161b22;border:1px solid #30363d;border-radius:6px;padding:8px 12px;color:#e6edf3;font-size:14px;width:300px; }
.count { color:#6e7681;font-size:13px; }
.table { width:100%;border-collapse:collapse;font-size:13px; }
.table th { text-align:left;padding:10px 12px;color:#6e7681;font-size:11px;text-transform:uppercase;border-bottom:1px solid #21262d; }
.table td { padding:10px 12px;border-bottom:1px solid #161b22;color:#e6edf3;vertical-align:middle; }
.table tr:hover td { background:#161b22; }
.table tr.absent td { opacity:.5; }
.dot { display:inline-block;width:8px;height:8px;border-radius:50%; }
.dot.active{background:#42b883;} .dot.absent{background:#f85149;} .dot.returned{background:#ffc107;}
.mono { font-family:monospace; }
.small { font-size:11px;color:#6e7681; }
.tag { background:#21262d;border-radius:4px;padding:2px 6px;font-size:10px;color:#8b949e;margin-right:4px; }
.act { background:#21262d;border:1px solid #30363d;color:#8b949e;padding:4px 8px;border-radius:4px;cursor:pointer;font-size:11px;margin-right:4px; }
.act.danger:hover { color:#f85149;border-color:#f85149; }
</style>
```

- [ ] **Step 12.3 : Créer `frontend/src/views/HostsView.vue`**

```vue
<template>
  <div>
    <h1 style="font-size:20px;font-weight:700;color:#e6edf3;margin:0 0 24px;">Hôtes réseau</h1>
    <div v-if="store.loading" style="color:#6e7681;">Chargement…</div>
    <HostTable v-else />
  </div>
</template>
<script setup lang="ts">
import { onMounted } from 'vue'
import HostTable from '../components/hosts/HostTable.vue'
import { useHostsStore } from '../stores/hosts'
const store = useHostsStore()
onMounted(() => store.fetchHosts())
</script>
```

- [ ] **Step 12.4 : Créer `frontend/src/views/ScansView.vue`**

```vue
<template>
  <div>
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:24px;">
      <h1 style="font-size:20px;font-weight:700;color:#e6edf3;">Scans Nmap</h1>
      <button class="btn-pri" @click="trigger" :disabled="running">{{ running ? 'En cours…' : '▶ Lancer un scan' }}</button>
    </div>
    <table class="table">
      <thead><tr><th>Date</th><th>Plage</th><th>Hôtes</th><th>Durée</th><th>Statut</th></tr></thead>
      <tbody>
        <tr v-for="s in scans" :key="s.id">
          <td>{{ fmt(s.started_at) }}</td><td class="mono">{{ s.range }}</td>
          <td>{{ s.hosts_found ?? '—' }}</td><td>{{ dur(s.started_at, s.finished_at) }}</td>
          <td><span class="badge" :class="s.status">{{ s.status }}</span></td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
<script setup lang="ts">
import { ref, onMounted } from 'vue'
const scans = ref<any[]>([])
const running = ref(false)
const fmt = (iso: string) => new Date(iso).toLocaleString('fr-FR')
const dur = (a: string, b: string|null) => { if(!b)return'—'; const s=Math.floor((new Date(b).getTime()-new Date(a).getTime())/1000); return s<60?`${s}s`:`${Math.floor(s/60)}m${s%60}s` }
async function fetch_() { const r=await fetch('/api/v1/scans?limit=50'); if(r.ok)scans.value=await r.json() }
async function trigger() { running.value=true; await fetch('/api/v1/scans/trigger',{method:'POST'}); setTimeout(async()=>{await fetch_();running.value=false},3000) }
onMounted(fetch_)
</script>
<style scoped>
.btn-pri{background:#4f8ef7;border:none;color:#fff;padding:8px 16px;border-radius:6px;cursor:pointer;font-weight:600;}
.btn-pri:disabled{opacity:.5;cursor:not-allowed;}
.table{width:100%;border-collapse:collapse;font-size:13px;}
.table th{text-align:left;padding:10px 12px;color:#6e7681;font-size:11px;text-transform:uppercase;border-bottom:1px solid #21262d;}
.table td{padding:10px 12px;border-bottom:1px solid #161b22;color:#e6edf3;}
.mono{font-family:monospace;}
.badge{border-radius:4px;padding:2px 8px;font-size:11px;font-weight:600;}
.badge.completed{background:rgba(66,184,131,.15);color:#42b883;}
.badge.running{background:rgba(79,142,247,.15);color:#4f8ef7;}
.badge.failed{background:rgba(248,81,73,.15);color:#f85149;}
</style>
```

- [ ] **Step 12.5 : Créer `frontend/src/views/SettingsView.vue`**

```vue
<template>
  <div>
    <h1 style="font-size:20px;font-weight:700;color:#e6edf3;margin:0 0 24px;">Paramètres</h1>
    <div class="section"><h2>Connexion Unraid</h2>
      <div class="fg"><label>IP du serveur</label><input v-model="cfg.UNRAID_HOST" class="inp" /></div>
      <div class="fg"><label>Port API</label><input v-model="cfg.UNRAID_API_PORT" class="inp" type="number" /></div>
    </div>
    <div class="section"><h2>Scan réseau</h2>
      <div class="fg"><label>Plage Nmap</label><input v-model="cfg.nmap_range" class="inp" /></div>
      <div class="fg"><label>Intervalle (secondes)</label><input v-model="cfg.nmap_interval" class="inp" type="number" /></div>
    </div>
    <div class="section"><h2>Métriques</h2>
      <div class="fg"><label>Intervalle de collecte (secondes)</label><input v-model="cfg.metrics_interval" class="inp" type="number" /></div>
    </div>
    <button class="btn-pri" @click="save">Enregistrer</button>
    <span v-if="ok" style="margin-left:12px;color:#42b883;font-size:13px;">✓ Enregistré</span>
  </div>
</template>
<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
const cfg = reactive<Record<string,string>>({})
const ok = ref(false)
onMounted(async () => { const r=await fetch('/api/v1/config'); if(r.ok) Object.assign(cfg,await r.json()) })
async function save() {
  await fetch('/api/v1/config',{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify(cfg)})
  ok.value=true; setTimeout(()=>ok.value=false,2000)
}
</script>
<style scoped>
.section{background:#161b22;border:1px solid #30363d;border-radius:8px;padding:20px;margin-bottom:16px;}
h2{font-size:14px;font-weight:600;color:#e6edf3;margin:0 0 16px;}
.fg{margin-bottom:14px;}
label{display:block;font-size:12px;color:#6e7681;margin-bottom:6px;}
.inp{width:100%;max-width:400px;background:#0d1117;border:1px solid #30363d;border-radius:6px;padding:8px 12px;color:#e6edf3;font-size:14px;}
.btn-pri{background:#4f8ef7;border:none;color:#fff;padding:10px 20px;border-radius:6px;cursor:pointer;font-weight:600;}
</style>
```

- [ ] **Step 12.6 : Créer les vues secondaires**

Créer `frontend/src/views/ContainersView.vue` :
```vue
<template>
  <div>
    <h1 style="font-size:20px;font-weight:700;color:#e6edf3;margin:0 0 24px;">Conteneurs Docker</h1>
    <div v-if="loading" style="color:#6e7681;">Chargement…</div>
    <table v-else class="table">
      <thead><tr><th>Statut</th><th>Nom</th><th>CPU</th><th>Mémoire</th></tr></thead>
      <tbody>
        <tr v-for="c in containers" :key="c.name">
          <td><span class="dot" :class="c.status"></span></td>
          <td>{{ c.name }}</td>
          <td>{{ c.status==='running'?(c.stats?.cpu??0).toFixed(2)+'%':'—' }}</td>
          <td>{{ c.status==='running'&&c.stats?.memory?(c.stats.memory/1024/1024).toFixed(0)+' MB':'—' }}</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
<script setup lang="ts">
import { ref, onMounted } from 'vue'
const containers=ref<any[]>([]);const loading=ref(true)
onMounted(async()=>{const r=await fetch('/api/v1/containers');if(r.ok)containers.value=await r.json();loading.value=false})
</script>
<style scoped>
.table{width:100%;border-collapse:collapse;font-size:13px;}
.table th{text-align:left;padding:10px 12px;color:#6e7681;font-size:11px;text-transform:uppercase;border-bottom:1px solid #21262d;}
.table td{padding:10px 12px;border-bottom:1px solid #161b22;color:#e6edf3;}
.dot{display:inline-block;width:8px;height:8px;border-radius:50%;}
.dot.running{background:#42b883;}.dot.stopped,.dot.exited{background:#f85149;}
</style>
```

Créer `frontend/src/views/VmsView.vue` :
```vue
<template>
  <div>
    <h1 style="font-size:20px;font-weight:700;color:#e6edf3;margin:0 0 24px;">Machines Virtuelles</h1>
    <table class="table">
      <thead><tr><th>Statut</th><th>Nom</th><th>vCPU</th><th>Mémoire</th></tr></thead>
      <tbody>
        <tr v-for="v in vms" :key="v.name">
          <td><span class="dot" :class="v.status"></span></td>
          <td>{{ v.name }}</td><td>{{ v.vcpus??'—' }}</td>
          <td>{{ v.memory?(v.memory/1024/1024/1024).toFixed(0)+' GB':'—' }}</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
<script setup lang="ts">
import { ref, onMounted } from 'vue'
const vms=ref<any[]>([])
onMounted(async()=>{const r=await fetch('/api/v1/vms');if(r.ok)vms.value=await r.json()})
</script>
<style scoped>
.table{width:100%;border-collapse:collapse;font-size:13px;}
.table th{text-align:left;padding:10px 12px;color:#6e7681;font-size:11px;text-transform:uppercase;border-bottom:1px solid #21262d;}
.table td{padding:10px 12px;border-bottom:1px solid #161b22;color:#e6edf3;}
.dot{display:inline-block;width:8px;height:8px;border-radius:50%;}
.dot.running{background:#42b883;}.dot.stopped,.dot.shutoff{background:#6e7681;}
</style>
```

Créer `frontend/src/views/NetworkView.vue` :
```vue
<template>
  <div>
    <h1 style="font-size:20px;font-weight:700;color:#e6edf3;margin:0 0 24px;">Réseau local</h1>
    <NetworkWidget style="max-width:500px;" />
    <div style="margin-top:20px;"><router-link to="/hosts" style="color:#4f8ef7;text-decoration:none;">Voir tous les hôtes →</router-link></div>
  </div>
</template>
<script setup lang="ts">
import NetworkWidget from '../components/widgets/NetworkWidget.vue'
</script>
```

Créer `frontend/src/views/UnraidView.vue` :
```vue
<template>
  <div>
    <h1 style="font-size:20px;font-weight:700;color:#e6edf3;margin:0 0 24px;">Unraid — Détail système</h1>
    <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:16px;">
      <KpiCard label="CPU" :value="(m.current.cpu??0).toFixed(1)+'%'" :percent="m.current.cpu" :warn="70" :danger="90" />
      <KpiCard label="RAM" :value="(m.current.ram_used_gb??0).toFixed(1)+' GB'" :percent="ramPct" :warn="80" :danger="90" />
      <KpiCard label="Temp. CPU" :value="(m.current.temp_cpu??0).toFixed(0)+'°C'" :percent="m.current.temp_cpu" :warn="70" :danger="85" />
      <KpiCard label="Uptime" :value="m.uptimeFormatted" />
    </div>
    <StorageWidget style="max-width:600px;" />
  </div>
</template>
<script setup lang="ts">
import { computed, onMounted } from 'vue'
import KpiCard from '../components/widgets/KpiCard.vue'
import StorageWidget from '../components/widgets/StorageWidget.vue'
import { useMetricsStore } from '../stores/metrics'
const m = useMetricsStore()
const ramPct = computed(()=>{ const t=m.current.ram_total_gb??0; return t>0?Math.round((m.current.ram_used_gb??0)/t*100):0 })
onMounted(()=>m.fetchCurrent())
</script>
```

- [ ] **Step 12.7 : Build final du frontend**

```bash
cd frontend && npm run build && cd ..
```
Attendu : build réussi, toutes les vues compilées

- [ ] **Step 12.8 : Commit**

```bash
git add frontend/src/
git commit -m "feat: all frontend views — hosts, scans, settings, containers, VMs, network, Unraid"
```

---

## Task 13 : Packaging Docker

**Files:**
- Create: `Dockerfile`
- Create: `docker-compose.yml`
- Create: `.dockerignore`

- [ ] **Step 13.1 : Créer `.dockerignore`**

```
__pycache__
*.pyc
.env
.git
.venv
node_modules
frontend/node_modules
tests/
.superpowers/
```

- [ ] **Step 13.2 : Créer `Dockerfile`**

```dockerfile
# Stage 1: Build Vue.js
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ .
RUN npm run build

# Stage 2: Image finale
FROM python:3.12-slim

RUN apt-get update && \
    apt-get install -y --no-install-recommends nmap && \
    rm -rf /var/lib/apt/lists/*

RUN mkdir -p /data

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ ./backend/
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

EXPOSE 8888

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8888/api/v1/config')"

VOLUME ["/data"]

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8888"]
```

- [ ] **Step 13.3 : Créer `docker-compose.yml`**

```yaml
services:
  lach-sentinel:
    build: .
    container_name: lach-sentinel
    restart: unless-stopped
    ports:
      - "8888:8888"
    volumes:
      - ./data:/data
    environment:
      - UNRAID_HOST=192.168.111.253
      - UNRAID_API_PORT=7443
      - UNRAID_API_KEY=${UNRAID_API_KEY}
      - NMAP_RANGE=192.168.111.0/24
      - NMAP_INTERVAL=3600
      - METRICS_INTERVAL=60
      - WS_PUSH_INTERVAL=5
      - TZ=Europe/Paris
    cap_add:
      - NET_ADMIN
      - NET_RAW
```

- [ ] **Step 13.4 : Builder l'image Docker**

```bash
docker compose build
```
Attendu : build réussi — frontend compilé, Python installé, nmap présent

- [ ] **Step 13.5 : Lancer et vérifier le démarrage**

```bash
echo "UNRAID_API_KEY=your_key_here" > .env
docker compose up -d
sleep 5
docker compose logs | head -20
```
Attendu : `lach-sentinel started — monitoring 192.168.111.253` dans les logs, aucune erreur fatale

- [ ] **Step 13.6 : Vérifier que l'API répond**

```bash
curl -s http://localhost:8888/api/v1/config | python3 -m json.tool
curl -s http://localhost:8888/api/v1/hosts
curl -o /dev/null -sw "%{http_code}" http://localhost:8888/
```
Attendu : config JSON avec les valeurs par défaut, `[]` pour les hôtes, `200` pour la SPA

- [ ] **Step 13.7 : Arrêter et committer**

```bash
docker compose down
git add Dockerfile docker-compose.yml .dockerignore
git commit -m "feat: Docker multi-stage build with nmap NET_ADMIN/NET_RAW capabilities"
```

---

## Task 14 : Intégration finale et tag

- [ ] **Step 14.1 : Lancer la suite de tests complète**

```bash
pytest tests/ -v
```
Attendu : tous les tests PASS. Corriger toute erreur avant de continuer.

- [ ] **Step 14.2 : Vérifier le build frontend**

```bash
cd frontend && npm run build && cd ..
```
Attendu : aucune erreur TypeScript

- [ ] **Step 14.3 : Smoke test Docker final**

```bash
docker compose build && docker compose up -d
sleep 8
curl -s http://localhost:8888/api/v1/config | python3 -m json.tool
docker compose logs --tail=10
docker compose down
```
Attendu : config JSON valide, logs sans erreurs `ERROR`

- [ ] **Step 14.4 : Tag de la release**

```bash
git tag v0.1.0
git log --oneline -15
```

- [ ] **Step 14.5 : Commit final**

```bash
git commit --allow-empty -m "release: v0.1.0 — lach-sentinel initial release"
```
