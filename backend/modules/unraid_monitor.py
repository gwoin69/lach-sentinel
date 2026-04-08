import json
import logging
import os
from configparser import ConfigParser
from datetime import datetime, timezone
from pathlib import Path

import httpx
from sqlalchemy.orm import Session

from backend.models import Metric

logger = logging.getLogger(__name__)

HOST_PROC = Path(os.getenv("HOST_PROC", "/host_proc"))
HOST_THERMAL = Path(os.getenv("HOST_THERMAL", "/host_thermal"))
HOST_STATE = Path(os.getenv("HOST_STATE", "/host_state"))
HOST_USER = Path(os.getenv("HOST_USER", "/host_user"))
DOCKER_SOCK = os.getenv("DOCKER_SOCK", "/var/run/docker.sock")


def _read_meminfo() -> dict[str, int]:
    result: dict[str, int] = {}
    try:
        for line in (HOST_PROC / "meminfo").read_text().splitlines():
            if ":" in line:
                key, val = line.split(":", 1)
                result[key.strip()] = int(val.strip().split()[0])
    except Exception as exc:
        logger.debug("meminfo read failed: %s", exc)
    return result


def _read_uptime() -> float:
    try:
        return float((HOST_PROC / "uptime").read_text().split()[0])
    except Exception as exc:
        logger.debug("uptime read failed: %s", exc)
        return 0.0


def _read_cpu_percent() -> float:
    try:
        cfg = ConfigParser()
        cfg.read(HOST_STATE / "cpuload.ini")
        return float(cfg["cpu"]["host"])
    except Exception as exc:
        logger.debug("cpuload read failed: %s", exc)
        return 0.0


def _read_cpu_temp() -> float:
    try:
        return int((HOST_THERMAL / "thermal_zone0" / "temp").read_text().strip()) / 1000.0
    except Exception as exc:
        logger.debug("cpu temp read failed: %s", exc)
        return 0.0


def _read_array_state() -> str:
    try:
        cfg = ConfigParser()
        cfg.read(HOST_STATE / "var.ini")
        return cfg[""]["mdState"].strip('"')
    except Exception as exc:
        logger.debug("var.ini read failed: %s", exc)
        return "unknown"


def _read_parity_status() -> str:
    try:
        cfg = ConfigParser()
        cfg.read(HOST_STATE / "disks.ini")
        return cfg["parity"]["status"].strip('"')
    except Exception as exc:
        logger.debug("disks.ini parity read failed: %s", exc)
        return "unknown"


def _read_array_capacity() -> tuple[float, float]:
    """Returns (used_tb, total_tb) from /mnt/user statvfs."""
    try:
        stat = os.statvfs(HOST_USER)
        total_bytes = stat.f_blocks * stat.f_frsize
        free_bytes = stat.f_bavail * stat.f_frsize
        used_bytes = total_bytes - free_bytes
        return used_bytes / 1024 ** 4, total_bytes / 1024 ** 4
    except Exception as exc:
        logger.debug("array capacity read failed: %s", exc)
        return 0.0, 0.0


async def _get_containers() -> list[dict]:
    try:
        transport = httpx.AsyncHTTPTransport(uds=DOCKER_SOCK)
        async with httpx.AsyncClient(transport=transport, base_url="http://docker") as client:
            resp = await client.get("/containers/json?all=true")
            resp.raise_for_status()
            return [
                {
                    "name": c["Names"][0].lstrip("/") if c["Names"] else c["Id"][:12],
                    "status": c["State"],
                }
                for c in resp.json()
            ]
    except Exception as exc:
        logger.warning("Docker socket read failed: %s", exc)
        return []


class UnraidMonitor:
    async def collect(self, db: Session) -> None:
        mem = _read_meminfo()
        ram_total_gb = mem.get("MemTotal", 0) / 1024 ** 2
        ram_used_gb = (mem.get("MemTotal", 0) - mem.get("MemAvailable", 0)) / 1024 ** 2

        cpu_usage = _read_cpu_percent()
        temp_cpu = _read_cpu_temp()
        uptime_seconds = _read_uptime()
        array_state = _read_array_state()
        array_used_tb, array_total_tb = _read_array_capacity()
        containers = await _get_containers()

        now = datetime.now(timezone.utc)
        metrics = [
            Metric(timestamp=now, type="cpu", value=cpu_usage),
            Metric(timestamp=now, type="ram_used_gb", value=ram_used_gb),
            Metric(timestamp=now, type="ram_total_gb", value=ram_total_gb),
            Metric(timestamp=now, type="temp_cpu", value=temp_cpu),
            Metric(timestamp=now, type="uptime_seconds", value=uptime_seconds),
            Metric(timestamp=now, type="array_state", value=1.0 if array_state == "STARTED" else 0.0,
                   meta=array_state),
            Metric(timestamp=now, type="array_used_tb", value=array_used_tb),
            Metric(timestamp=now, type="array_total_tb", value=array_total_tb),
            Metric(timestamp=now, type="containers", value=float(len(containers)),
                   meta=json.dumps(containers)),
        ]
        db.add_all(metrics)
        db.commit()
        logger.debug("Metrics collected: cpu=%.1f%% ram=%.1f/%.1fGB temp=%.1f°C",
                     cpu_usage, ram_used_gb, ram_total_gb, temp_cpu)
