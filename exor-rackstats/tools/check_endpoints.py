"""Verify the shared schema. Authentication token is read from environment/env file."""
import argparse
import json
import os
from pathlib import Path
import ssl
import sys
from urllib.request import Request, urlopen
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "server"))
from rackstats_agent.__main__ import load_env

parser = argparse.ArgumentParser()
parser.add_argument("--demo", action="store_true")
parser.add_argument("--env")
parser.add_argument("--url")
parser.add_argument("--ca-file", default="")
args = parser.parse_args()
if args.env: load_env(args.env)
token = "local-demo-token" if args.demo else os.environ.get("RACKSTATS_TOKEN", "")
if not token: parser.error("Set RACKSTATS_TOKEN in the environment or use --env")
urls = ["http://127.0.0.1:4300/api/v1/stats", "http://127.0.0.1:4310/api/v1/stats"] if args.demo else [args.url]
if not all(urls): parser.error("Supply --url for a live collector")
for url in urls:
    request = Request(url, headers={"Authorization": "Bearer " + token})
    context = ssl.create_default_context(cafile=args.ca_file or None)
    with urlopen(request, timeout=5, context=context) as response: data = json.load(response)
    assert data["schema_version"] == 1
    assert data["source"] in ("nas", "proxmox")
    assert data["state"] in ("fresh", "stale", "unavailable")
    assert data.get("host") is not None, "Collector has no successful sample"
    for metric in ("memory", "storage"):
        assert "percent" in data["host"][metric]
    print(json.dumps({"url": url, "source": data["source"], "state": data["state"],
                      "cpu_percent": data["host"]["cpu_percent"], "vm_count": len(data["vms"])}))
