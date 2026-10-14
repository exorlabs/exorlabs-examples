import json
from pathlib import Path
import shutil
import ssl
import subprocess
import sys
import tempfile
import threading
import unittest
from urllib.error import URLError
from urllib.request import Request, urlopen
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "server"))
from rackstats_agent.collectors import DemoCollector
from rackstats_agent.service import SnapshotStore, make_server


@unittest.skipUnless(shutil.which("openssl"), "OpenSSL is required for the TLS integration test")
class TLSTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.certs = Path(cls.temp.name) / "certs"
        subprocess.run([sys.executable, str(ROOT / "tools/make_tls.py"), "--nas-ip", "127.0.0.1",
                        "--proxmox-collector-ip", "127.0.0.1", "--out", str(cls.certs)], check=True, capture_output=True)
        cls.store = SnapshotStore(DemoCollector(), "nas"); cls.store.refresh()
        cls.server = make_server(cls.store, "tls-fixture-token", cert=str(cls.certs / "nas.crt"), key=str(cls.certs / "nas.key"))
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True); cls.thread.start()
        cls.url = f"https://127.0.0.1:{cls.server.server_port}/api/v1/stats"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown(); cls.server.server_close(); cls.thread.join(timeout=2); cls.temp.cleanup()

    def test_trusted_ca_and_authenticated_https(self):
        context = ssl.create_default_context(cafile=str(self.certs / "ca.crt"))
        request = Request(self.url, headers={"Authorization": "Bearer tls-fixture-token"})
        with urlopen(request, timeout=3, context=context) as response: data = json.load(response)
        self.assertEqual(data["state"], "fresh")
        self.assertEqual(data["source"], "nas")

    def test_untrusted_certificate_is_rejected(self):
        request = Request(self.url, headers={"Authorization": "Bearer tls-fixture-token"})
        with self.assertRaises(URLError): urlopen(request, timeout=3, context=ssl.create_default_context())


if __name__ == "__main__": unittest.main(verbosity=2)
