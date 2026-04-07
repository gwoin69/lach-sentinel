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
