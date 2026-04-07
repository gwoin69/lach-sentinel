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
        try:
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
        finally:
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
    except (WebSocketDisconnect, Exception):
        pass
    finally:
        ws_manager.disconnect(websocket)


if FRONTEND_DIR.exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIR / "assets"), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa_fallback(full_path: str):
        return FileResponse(FRONTEND_DIR / "index.html")
