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

            # Mark hosts not found as absent
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
