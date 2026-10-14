"""Start two explicitly simulated endpoints for first-run API/firmware checks."""
import argparse
import sys
from pathlib import Path
import threading
import time
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "server"))
from rackstats_agent.collectors import DemoCollector
from rackstats_agent.service import SnapshotStore, make_server

parser = argparse.ArgumentParser()
parser.add_argument("--bind", default="127.0.0.1", help="Use your computer's LAN IP only for an ESP32 demo")
args = parser.parse_args()
resources = []
try:
    for source, port in (("nas", 4300), ("proxmox", 4310)):
        store = SnapshotStore(DemoCollector(source), source, interval=2)
        store.start()
        server = make_server(store, "local-demo-token", args.bind, port)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        resources.append((server, store))
        print(f"SIMULATED {source}: http://{args.bind}:{port}/api/v1/stats", flush=True)
    print("Bearer token: local-demo-token (public fixture, never use for live stats)", flush=True)
    while True: time.sleep(1)
except KeyboardInterrupt: pass
finally:
    for server, store in resources:
        server.shutdown(); server.server_close(); store.close()
