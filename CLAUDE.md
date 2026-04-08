# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**lach-sentinel** is a self-hosted network monitoring dashboard for Unraid servers. It combines:
- A **FastAPI** backend (Python 3.12) that runs nmap scans, collects Unraid metrics via its API, stores data in SQLite, and pushes live updates via WebSocket.
- A **Vue 3 + TypeScript** frontend (Vite, Pinia, Chart.js) served as a SPA from the same process on port 8888.
- Deployment as a single Docker container (multi-stage build) requiring `NET_ADMIN` + `NET_RAW` capabilities for nmap.

## Commands

### Backend

```bash
# Install dependencies
pip install -r requirements.txt -r requirements-dev.txt

# Run dev server (backend only, no frontend dist needed)
TESTING=false UNRAID_HOST=... UNRAID_API_KEY=... uvicorn backend.main:app --reload --port 8888

# Run all tests
pytest

# Run a single test file
pytest tests/test_api_hosts.py

# Run a single test
pytest tests/test_api_hosts.py::test_function_name
```

### Frontend

```bash
cd frontend
npm install
npm run dev        # dev server with HMR (proxies /api to backend)
npm run build      # compiles to frontend/dist/ (picked up by FastAPI)
```

### Docker

```bash
docker compose up --build     # build and start
docker compose up -d          # detached
```

## Architecture

### Backend structure

```
backend/
  main.py          # FastAPI app, lifespan (DB init, scheduler start), WebSocket endpoint, SPA fallback
  config.py        # Pydantic Settings — reads env vars (UNRAID_HOST, UNRAID_API_KEY, NMAP_RANGE, etc.)
  database.py      # SQLAlchemy engine + Base + SessionLocal (SQLite at /data/sentinel.db)
  models.py        # ORM models: Host, Service, ScanResult, Metric, MetricHourly, MetricDaily, ConfigEntry
  scheduler.py     # APScheduler setup: collect_metrics, run_nmap, run_retention (interval-based)
  api/             # FastAPI routers: hosts, scans, metrics, containers, vms, config_api
  modules/
    unraid_monitor.py   # Polls Unraid GraphQL/REST API, writes Metric rows
    nmap_scanner.py     # Runs nmap, upserts Host + Service rows, writes ScanResult
    retention.py        # Rolls up raw metrics → hourly/daily, prunes old raw rows
    alert_engine.py     # Alert logic (threshold checks)
  ws/
    manager.py     # WebSocketManager — broadcast dict payloads to all connected clients
```

### Key data flows

1. **Metrics**: `scheduler → unraid_monitor.collect()` → writes `Metric` rows → broadcasts `{type: "metrics_update"}` via WebSocket.
2. **Nmap scans**: `scheduler → nmap_scanner.scan()` (runs in executor, blocking) → upserts `Host`/`Service`, writes `ScanResult`.
3. **Retention**: hourly job rolls raw `Metric` → `MetricHourly`/`MetricDaily`, then prunes raw data.
4. **API**: REST endpoints under `/api/v1/` serve CRUD for hosts, scans, metrics history, containers, VMs, and config.
5. **Frontend**: WebSocket store (`stores/ws.ts`) connects to `/ws`, dispatches updates to Pinia stores; views consume stores.

### Testing

Tests use `TESTING=true` env var (set in `conftest.py`) to skip scheduler/DB init in lifespan. The `test_engine` fixture creates an in-memory SQLite DB per test; `db_session` provides a session. FastAPI tests use `httpx.AsyncClient` with `ASGITransport`.

Setting `TESTING=true` before importing backend modules is critical — it must be set in `conftest.py` before any backend import.

## Deployment

Deployed to Unraid at `192.168.111.253` via rsync + `docker compose` over SSH. See project memory for deployment details.
