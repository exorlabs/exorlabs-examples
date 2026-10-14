import argparse
import os
from pathlib import Path
from .collectors import DemoCollector, LinuxCollector, ProxmoxCollector
from .service import SnapshotStore, make_server


def load_env(path):
    for line in Path(path).read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"): continue
        name, sep, value = line.partition("=")
        if not sep or not name.strip().replace("_", "").isalnum(): raise ValueError("Invalid env file line")
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'": value = value[1:-1]
        os.environ.setdefault(name.strip(), value)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--env", help="Optional local env file; existing environment wins")
    args = parser.parse_args()
    if args.env: load_env(args.env)
    e = os.environ
    mode = e.get("RACKSTATS_MODE", "nas")
    source = e.get("RACKSTATS_DEMO_SOURCE", "nas") if mode == "demo" else mode
    if source not in ("nas", "proxmox"): parser.error("Mode/source must be nas, proxmox or demo")
    token = e.get("RACKSTATS_TOKEN", "")
    if not token or (mode != "demo" and (len(token) < 24 or "REPLACE" in token or token == "local-demo-token")):
        parser.error("Set a random RACKSTATS_TOKEN (at least 24 characters for live modes)")
    host = e.get("RACKSTATS_BIND", "127.0.0.1")
    cert, key = e.get("RACKSTATS_TLS_CERT", ""), e.get("RACKSTATS_TLS_KEY", "")
    if host not in ("127.0.0.1", "localhost", "::1") and not cert and e.get("RACKSTATS_ALLOW_HTTP", "0") != "1":
        parser.error("Remote binding requires TLS; explicit RACKSTATS_ALLOW_HTTP=1 is available for a trusted LAN lab")
    interval = float(e.get("RACKSTATS_INTERVAL", "5"))
    if not 1 <= interval <= 300: parser.error("Sample interval must be between 1 and 300 seconds")
    if mode == "demo": collector = DemoCollector(source)
    elif mode == "nas":
        collector = LinuxCollector(e.get("RACKSTATS_PROC_ROOT", "/proc"), e.get("RACKSTATS_STORAGE_PATH", "/"),
                                   e.get("RACKSTATS_INTERFACE", "eth0"), e.get("RACKSTATS_TEMPERATURE_FILE", ""),
                                   e.get("RACKSTATS_LABEL", "Synology"))
    else:
        required = ("PVE_URL", "PVE_NODE", "PVE_TOKEN_ID", "PVE_TOKEN_SECRET")
        if any(not e.get(name) or "REPLACE" in e[name] for name in required): parser.error("Fill in the four PVE settings")
        collector = ProxmoxCollector(e["PVE_URL"], e["PVE_NODE"], e["PVE_TOKEN_ID"], e["PVE_TOKEN_SECRET"],
                                     e.get("PVE_CA_FILE", ""), e.get("RACKSTATS_LABEL", "Proxmox"))
    store = SnapshotStore(collector, source, interval)
    store.start()
    server = make_server(store, token, host, int(e.get("RACKSTATS_PORT", "4310" if source == "proxmox" else "4300")), cert, key)
    scheme = "https" if cert else "http"
    print(f"Stats service: {scheme}://{host}:{server.server_port}/api/v1/stats (Bearer token required)", flush=True)
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally:
        server.server_close()
        store.close()


if __name__ == "__main__": main()
