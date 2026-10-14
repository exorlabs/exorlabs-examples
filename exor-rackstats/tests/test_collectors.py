import json
import os
from pathlib import Path
import ssl
import sys
import tempfile
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "server"))
from rackstats_agent.collectors import LinuxCollector, ProxmoxCollector, DemoCollector
from rackstats_agent.service import SnapshotStore, make_server


class LinuxTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.proc = Path(self.temp.name)
        (self.proc / "net").mkdir()
        (self.proc / "meminfo").write_text("MemTotal: 8192 kB\nMemAvailable: 2048 kB\n")
        (self.proc / "uptime").write_text("12345.00 54321.00\n")
        self.write_counters(100, 900, 1000, 2000)
        self.now = 0.0
        self.collector = LinuxCollector(self.proc, self.proc, "eth0", clock=lambda: self.now)

    def tearDown(self): self.temp.cleanup()

    def write_counters(self, busy, idle, rx, tx):
        (self.proc / "stat").write_text(f"cpu {busy} 0 0 {idle} 0 0 0 0 90000 90000\n")
        (self.proc / "net/dev").write_text(f"eth0: {rx} 0 0 0 0 0 0 0 {tx} 0 0 0 0 0 0 0\n")

    def test_cpu_guest_counters_not_double_counted(self):
        self.collector.collect()
        self.now = 2
        self.write_counters(150, 1050, 3000, 6000)
        result = self.collector.collect()["host"]
        self.assertEqual(result["cpu_percent"], 25.0)
        self.assertEqual(result["network"]["rx_bytes_per_second"], 1000)
        self.assertEqual(result["network"]["tx_bytes_per_second"], 2000)

    def test_initial_deltas_and_temperature_are_unknown(self):
        result = self.collector.collect()["host"]
        self.assertIsNone(result["cpu_percent"])
        self.assertIsNone(result["network"]["rx_bytes_per_second"])
        self.assertIsNone(result["temperature_c"])
        self.assertEqual(result["memory"]["percent"], 75.0)
        self.assertGreater(result["storage"]["total_bytes"], 0)

    def test_reset_counters_do_not_produce_negative_rates(self):
        self.collector.collect()
        self.now = 2
        self.write_counters(1, 2, 3, 4)
        result = self.collector.collect()["host"]
        self.assertIsNone(result["network"]["tx_bytes_per_second"])
        self.assertIsNone(result["cpu_percent"])


class PVEFixtureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        class MockPVE(BaseHTTPRequestHandler):
            def log_message(self, *_): pass
            def do_GET(self):
                if self.headers.get("Authorization") != "PVEAPIToken=stats@pve!display=fixture-secret":
                    self.send_error(401); return
                if self.path == "/api2/json/nodes/pve/status":
                    data = {"cpu": 0.25, "memory": {"used": 3 * 1024**3, "total": 8 * 1024**3},
                            "rootfs": {"used": 20 * 1024**3, "total": 100 * 1024**3}, "uptime": 12345}
                elif self.path == "/api2/json/cluster/resources?type=vm":
                    data = [{"vmid": 100, "node": "pve", "type": "qemu", "name": "Fixture VM", "status": "running",
                             "cpu": 0.1, "mem": 1024**3, "maxmem": 4 * 1024**3},
                            {"vmid": 200, "node": "other", "type": "lxc", "status": "running"}]
                elif self.path.startswith("/api2/json/nodes/pve/rrddata?"):
                    data = [{"time": time.time()-60, "netin": 1234, "netout": 5678}, {"time": time.time(), "netin": None, "netout": None}]
                else:
                    self.send_error(404); return
                body = json.dumps({"data": data}).encode()
                self.send_response(200); self.send_header("Content-Length", str(len(body)))
                self.end_headers(); self.wfile.write(body)
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), MockPVE)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.url = f"http://127.0.0.1:{cls.server.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown(); cls.server.server_close(); cls.thread.join(timeout=2)

    def test_real_http_adapter_normalizes_host_vms_and_rrd(self):
        result = ProxmoxCollector(self.url, "pve", "stats@pve!display", "fixture-secret").collect()
        self.assertEqual(result["host"]["cpu_percent"], 25)
        self.assertEqual(result["host"]["memory"]["percent"], 37.5)
        self.assertEqual(result["host"]["storage"]["percent"], 20)
        self.assertEqual(result["host"]["network"]["rx_bytes_per_second"], 1234)
        self.assertEqual(len(result["vms"]), 1)
        self.assertEqual(result["vm_summary"], {"total": 1, "running": 1})
        self.assertEqual(result["vms"][0]["cpu_percent"], 10)
        self.assertIsNone(result["host"]["temperature_c"])

    def test_authentication_failure_propagates(self):
        with self.assertRaises(HTTPError) as error:
            ProxmoxCollector(self.url, "pve", "stats@pve!display", "wrong").collect()
        self.assertEqual(error.exception.code, 401)
        error.exception.close()

    def test_remote_plain_http_is_rejected(self):
        with self.assertRaises(ValueError): ProxmoxCollector("http://example.com:8006", "pve", "x", "y")


class StoreAndHTTPTests(unittest.TestCase):
    def test_failed_collection_keeps_previous_data_and_marks_stale(self):
        collector = DemoCollector()
        now = [0]
        store = SnapshotStore(collector, "nas", clock=lambda: now[0])
        store.refresh()
        initial = store.payload()[1]["host"]["cpu_percent"]
        def broken(): raise TimeoutError("No credentials in this error")
        collector.collect = broken
        now[0] = 9
        store.refresh()
        code, data = store.payload()
        self.assertEqual(code, 200); self.assertEqual(data["state"], "stale")
        self.assertEqual(data["host"]["cpu_percent"], initial); self.assertEqual(data["age_seconds"], 9)

    def test_no_first_sample_is_503(self):
        store = SnapshotStore(DemoCollector(), "nas")
        code, data = store.payload()
        self.assertEqual(code, 503); self.assertIsNone(data["host"])

    def test_http_auth_alias_and_json_schema(self):
        store = SnapshotStore(DemoCollector(), "nas")
        store.refresh()
        server = make_server(store, "fixture-token")
        thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
        try:
            base = f"http://127.0.0.1:{server.server_port}"
            with self.assertRaises(HTTPError) as error: urlopen(base + "/nas-stats", timeout=3)
            self.assertEqual(error.exception.code, 401); error.exception.close()
            req = Request(base + "/nas-stats", headers={"Authorization": "Bearer fixture-token"})
            with urlopen(req, timeout=3) as response: data = json.load(response)
            self.assertEqual(data["schema_version"], 1)
            self.assertEqual(data["state"], "fresh")
            self.assertEqual(data["source"], "nas")
            self.assertIn("simulated_data", data["warnings"])
        finally:
            server.shutdown(); server.server_close(); thread.join(timeout=2)


if __name__ == "__main__": unittest.main(verbosity=2)
