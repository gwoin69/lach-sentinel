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
