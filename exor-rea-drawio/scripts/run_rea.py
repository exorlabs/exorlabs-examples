"""Analyze draw.io's real downloaded artifacts using the unmodified REA CLI."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument("--command", default="rea", help="rea executable, or npx for the pinned npm package")
parser.add_argument("--timeout", type=int, default=600, help="Analysis timeout in seconds")
args = parser.parse_args()
target = ROOT / "upstream/drawio"
if not (target / "app.min.js").is_file():
    raise SystemExit("Download the real app first: node tools/fetch_upstream.mjs")
exe = shutil.which(args.command)
if not exe:
    raise SystemExit("Install REA: npm install --global rea-agents@6.4.0")
command = [exe]
if Path(exe).stem.lower().startswith("npx"):
    command += ["--yes", "rea-agents@6.4.0"]
command += ["analyze-javascript-application", str(target), "--format", "json"]
output = ROOT / "artifacts/rea-analysis.json"
output.parent.mkdir(parents=True, exist_ok=True)
with output.open("w") as stream:
    try:
        result = subprocess.run(command, text=True, stdout=stream, timeout=args.timeout)
    except subprocess.TimeoutExpired:
        raise SystemExit("REA timed out; any saved partial output must not be called a completed analysis.")
if result.returncode:
    sys.stderr.write(output.read_text()[:3000])
    raise SystemExit("REA did not complete; the saved output is an error report, not evidence of a successful analysis.")
evidence = json.loads(output.read_text())
if any(k in evidence for k in ("error", "code")):
    raise SystemExit("REA returned an error envelope; inspect the saved output.")
print(f"REA analysis saved: {output}")
