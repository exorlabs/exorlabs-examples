import argparse
from pathlib import Path
import re

parser = argparse.ArgumentParser()
parser.add_argument("url")
args = parser.parse_args()
url = args.url.rstrip("/")
if not re.fullmatch(r"https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", url):
    parser.error("Use the public GitHub repository URL, without .git or a tree/blob path")
if url.endswith(".git"): parser.error("Omit the .git suffix")
root = Path(__file__).resolve().parents[1]
for project in ("exor-rea-drawio", "exor-rackstats"):
    path = root / project / "docs/BLOG.md"
    text = path.read_text()
    if "REPOSITORY_URL" not in text:
        print(f"No placeholder remains in {path}; review its existing links manually")
        continue
    path.write_text(text.replace("REPOSITORY_URL", url))
    print(f"Updated {path.relative_to(root)}")
