import json
import math
import os
from pathlib import Path
import ssl
import time
from urllib.parse import quote, urlsplit
from urllib.request import Request, build_opener, HTTPSHandler, HTTPRedirectHandler


def number(value):
    return float(value) if type(value) in (int, float) and math.isfinite(value) else None


def percent(used, total):
    used, total = number(used), number(total)
    return round(max(0.0, min(100.0, used / total * 100)), 2) if used is not None and total and total > 0 else None


def capacity(used=None, total=None):
    return {"used_bytes": int(used) if number(used) is not None else None,
            "total_bytes": int(total) if number(total) is not None else None,
            "percent": percent(used, total)}


class LinuxCollector:
    """Read host procfs and statvfs; never infer Docker cgroup limits as NAS RAM."""
    def __init__(self, proc_root="/proc", storage_path="/", interface="eth0", temperature_file="", label="NAS", clock=time.monotonic):
        self.proc = Path(proc_root)
        self.storage = storage_path
        self.interface = interface
        self.temperature_file = temperature_file
        self.label = label
        self.clock = clock
        self.previous = None

    def collect(self):
        raw = (self.proc / "stat").read_text().splitlines()[0].split()
        if raw[0] != "cpu" or len(raw) < 5:
            raise ValueError("Missing aggregate CPU counters")
        cpu = [int(x) for x in raw[1:9]]
        total, idle = sum(cpu), cpu[3] + (cpu[4] if len(cpu) > 4 else 0)
        now = self.clock()
        counters = None
        for line in (self.proc / "net/dev").read_text().splitlines():
            if ":" not in line: continue
            name, fields = line.split(":", 1)
            values = fields.split()
            if name.strip() == self.interface and len(values) >= 9:
                counters = (int(values[0]), int(values[8]))
                break
        cpu_percent = rx = tx = None
        if self.previous:
            previous_total, previous_idle, previous_counters, previous_time = self.previous
            delta_total = total - previous_total
            delta_idle = idle - previous_idle
            if delta_total > 0 and delta_idle >= 0:
                cpu_percent = round(max(0.0, min(100.0, (delta_total - delta_idle) / delta_total * 100)), 2)
            elapsed = now - previous_time
            if counters and previous_counters and elapsed > 0:
                drx, dtx = counters[0] - previous_counters[0], counters[1] - previous_counters[1]
                if drx >= 0 and dtx >= 0:
                    rx, tx = round(drx / elapsed, 2), round(dtx / elapsed, 2)
        self.previous = total, idle, counters, now
        memory = {}
        for line in (self.proc / "meminfo").read_text().splitlines():
            name, value = line.split(":", 1)
            parts = value.split()
            memory[name] = int(parts[0]) * 1024
        mem_total, available = memory.get("MemTotal"), memory.get("MemAvailable")
        mem_used = mem_total - available if mem_total is not None and available is not None else None
        filesystem = os.statvfs(self.storage)
        disk_total = filesystem.f_blocks * filesystem.f_frsize
        disk_used = (filesystem.f_blocks - filesystem.f_bfree) * filesystem.f_frsize
        temperature = None
        if self.temperature_file:
            try:
                temperature = float(Path(self.temperature_file).read_text().strip()) / 1000
                if not math.isfinite(temperature): temperature = None
            except (OSError, ValueError):
                pass
        return {"host": {"name": self.label, "cpu_percent": cpu_percent,
                         "memory": capacity(mem_used, mem_total), "storage": capacity(disk_used, disk_total),
                         "temperature_c": temperature, "uptime_seconds": float((self.proc / "uptime").read_text().split()[0]),
                         "network": {"interface": self.interface, "rx_bytes_per_second": rx, "tx_bytes_per_second": tx}},
                "vms": [], "vm_summary": {"total": 0, "running": 0},
                "warnings": ["network_interface_unavailable"] if counters is None else []}


class ProxmoxCollector:
    def __init__(self, url, node, token_id, token_secret, ca_file="", label="Proxmox", timeout=4):
        parts = urlsplit(url)
        if parts.username or parts.password or parts.query or parts.fragment or parts.path not in ("", "/"):
            raise ValueError("PVE_URL must be an origin without embedded credentials")
        if parts.scheme != "https" and not (parts.scheme == "http" and parts.hostname in ("127.0.0.1", "localhost")):
            raise ValueError("PVE API must use HTTPS; HTTP is allowed only for local tests")
        if not parts.hostname: raise ValueError("PVE URL has no hostname")
        self.base = url.rstrip("/") + "/api2/json"
        self.node, self.label = node, label
        self.auth = f"PVEAPIToken={token_id}={token_secret}"
        self.ssl = ssl.create_default_context(cafile=ca_file or None)
        class NoRedirect(HTTPRedirectHandler):
            def redirect_request(self, *_args, **_kwargs): return None
        self.opener = build_opener(HTTPSHandler(context=self.ssl), NoRedirect())
        self.timeout = timeout

    def get(self, path):
        request = Request(self.base + path, headers={"Authorization": self.auth, "Accept": "application/json"})
        with self.opener.open(request, timeout=self.timeout) as response:
            body = response.read(1_048_577)
        if len(body) > 1_048_576: raise ValueError("PVE response exceeds size budget")
        payload = json.loads(body)
        if not isinstance(payload, dict) or "data" not in payload: raise ValueError("Unexpected PVE envelope")
        return payload["data"]

    def collect(self):
        node_path = quote(self.node, safe="")
        status = self.get(f"/nodes/{node_path}/status")
        if not isinstance(status, dict): raise ValueError("Unexpected node status")
        mem, disk = status.get("memory") or {}, status.get("rootfs") or {}
        cpu = number(status.get("cpu"))
        vms, warnings = [], []
        vm_summary = {"total": None, "running": None}
        try:
            resources = self.get("/cluster/resources?type=vm")
            if not isinstance(resources, list): raise ValueError("Unexpected VM inventory")
            selected = [vm for vm in resources if vm.get("node") == self.node and vm.get("type") in ("qemu", "lxc")]
            vm_summary = {"total": len(selected), "running": sum(vm.get("status") == "running" for vm in selected)}
            for vm in selected:
                if len(vms) >= 20:
                    warnings.append("vm_inventory_capped_at_20")
                    break
                vm_cpu = number(vm.get("cpu"))
                vms.append({"id": vm.get("vmid"), "kind": vm["type"], "name": vm.get("name", str(vm.get("vmid"))),
                            "status": vm.get("status", "unknown"), "cpu_percent": round(vm_cpu * 100, 2) if vm_cpu is not None else None,
                            "memory": capacity(vm.get("mem"), vm.get("maxmem"))})
        except (OSError, ValueError, KeyError):
            warnings.append("vm_inventory_unavailable")
        rx = tx = network_age = None
        try:
            rows = self.get(f"/nodes/{node_path}/rrddata?timeframe=hour&cf=AVERAGE")
            if isinstance(rows, list):
                for row in reversed(rows):
                    sample_time = number(row.get("time"))
                    if sample_time is not None and 0 <= time.time() - sample_time <= 180 and number(row.get("netin")) is not None and number(row.get("netout")) is not None:
                        rx, tx = number(row["netin"]), number(row["netout"])
                        network_age = round(time.time() - sample_time, 2)
                        break
        except (OSError, ValueError, KeyError):
            warnings.append("network_rrd_unavailable")
        return {"host": {"name": self.label, "cpu_percent": round(max(0, min(100, cpu * 100)), 2) if cpu is not None else None,
                         "memory": capacity(mem.get("used"), mem.get("total")), "storage": capacity(disk.get("used"), disk.get("total")),
                         "temperature_c": None, "uptime_seconds": number(status.get("uptime")),
                         "network": {"interface": "node aggregate (RRD average)", "sample_age_seconds": network_age,
                                     "rx_bytes_per_second": rx, "tx_bytes_per_second": tx}},
                "vms": vms, "vm_summary": vm_summary, "warnings": warnings}


class DemoCollector:
    def __init__(self, source="nas"):
        self.source, self.count = source, 0

    def collect(self):
        self.count += 1
        return {"host": {"name": "Demo NAS" if self.source == "nas" else "Demo Proxmox", "cpu_percent": 18 + self.count % 30,
                         "memory": capacity(3 * 1024**3, 8 * 1024**3), "storage": capacity(2 * 1024**4, 6 * 1024**4),
                         "temperature_c": 42, "uptime_seconds": 86400,
                         "network": {"interface": "simulated", "rx_bytes_per_second": 120000, "tx_bytes_per_second": 34000}},
                "vms": [{"id": 100, "kind": "qemu", "name": "Demo VM", "status": "running", "cpu_percent": 4,
                         "memory": capacity(1 * 1024**3, 4 * 1024**3)}] if self.source == "proxmox" else [],
                "vm_summary": {"total": 1 if self.source == "proxmox" else 0, "running": 1 if self.source == "proxmox" else 0},
                "warnings": ["simulated_data"]}
