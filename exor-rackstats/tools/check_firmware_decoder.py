"""Exercise the exact firmware JSON decoder with real HTTP service responses.
Usage: python3 tools/check_firmware_decoder.py /path/to/native-decode
No Proxmox/Synology credentials are used; API fixture normalization is tested separately.
"""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
from urllib.request import Request, urlopen
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "server"))
from rackstats_agent.collectors import DemoCollector
from rackstats_agent.service import SnapshotStore, make_server

parser = argparse.ArgumentParser()
parser.add_argument("decoder")
args = parser.parse_args()
with tempfile.TemporaryDirectory() as directory:
    for source in ("nas", "proxmox"):
        store = SnapshotStore(DemoCollector(source), source); store.refresh()
        server = make_server(store, "decoder-fixture-token")
        thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
        try:
            request = Request(f"http://127.0.0.1:{server.server_port}/api/v1/stats",
                              headers={"Authorization": "Bearer decoder-fixture-token"})
            with urlopen(request, timeout=3) as response: data = json.load(response)
            payload = Path(directory) / f"{source}.json"; payload.write_text(json.dumps(data))
            subprocess.run([args.decoder, str(payload), source], check=True)
            data["host"]["cpu_percent"] = None
            data["host"]["temperature_c"] = None
            data["state"] = "stale"
            payload.write_text(json.dumps(data))
            checked = subprocess.run([args.decoder, str(payload), source], check=True, capture_output=True, text=True)
            if "cpu=nan" not in checked.stdout or "stale=1" not in checked.stdout:
                raise SystemExit("Null/stale fields were not preserved by the decoder")
            print(checked.stdout.strip())
            data["schema_version"] = 999; payload.write_text(json.dumps(data))
            result = subprocess.run([args.decoder, str(payload), source], capture_output=True)
            if result.returncode != 1: raise SystemExit("Decoder did not reject unsupported schema")
        finally:
            server.shutdown(); server.server_close(); thread.join(timeout=2)
print("PASS: live HTTP payloads, null metrics, stale state and schema rejection through the firmware decoder.")
