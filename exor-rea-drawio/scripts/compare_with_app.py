"""Compare our independent codec with functions from the real draw.io bundle."""
import json
from pathlib import Path
import random
import subprocess
import sys
import xml.etree.ElementTree as ET
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from drawio_unpack import decode_page_text, encode_page_text, unpack_document, summarize


def application(requests):
    checked = subprocess.run(["node", str(ROOT / "tools/application_codec.mjs")],
                             input=json.dumps(requests, ensure_ascii=False), text=True,
                             capture_output=True, timeout=30)
    if checked.returncode:
        raise SystemExit(checked.stderr + "Run node tools/fetch_upstream.mjs first.")
    return json.loads(checked.stdout)


def main():
    requests, originals = [], []
    for name in ("aws-robot.drawio", "C4.drawio", "CSVimport-examples.drawio"):
        file = ROOT / "upstream/examples" / name
        source = ET.parse(file).getroot()
        decoded = unpack_document(file.read_text())
        print(name + ": " + ", ".join(f"{p['name']} ({p['cells']} cells)" for p in summarize(decoded)))
        for page in source.findall("diagram"):
            if len(page): raise SystemExit("Pinned example unexpectedly changed to plain XML")
            requests.append({"operation": "decompress", "value": page.text})
            originals.append(decode_page_text(page.text))
    assert application(requests) == originals, "Official-file decoding differs from the application"
    print(f"PASS: {len(originals)} pages from 3 official diagrams match the real app's decoder.")

    rng = random.Random(20261012)
    alphabet = "NAS + Proxmox 50% & <>!? é 北 😀"
    labels = ["", "NAS + Proxmox", "50% & <XML>", "Montréal / 北 / 😀", "!*'()~"]
    labels += ["".join(rng.choice(alphabet) for _ in range(rng.randrange(1, 180))) for _ in range(95)]
    models = []
    for index, label in enumerate(labels):
        graph = ET.Element("mxGraphModel")
        root = ET.SubElement(graph, "root")
        ET.SubElement(root, "mxCell", {"id": str(index), "value": label, "vertex": "1"})
        models.append(ET.tostring(graph, encoding="unicode"))
    real_payloads = application([{"operation": "compress", "value": xml} for xml in models])
    assert [decode_page_text(p) for p in real_payloads] == models
    recovered = application([{"operation": "decompress", "value": encode_page_text(xml)} for xml in models])
    assert recovered == models
    print("PASS: 100 cases in both directions, including Unicode, percent signs and plus signs.")


if __name__ == "__main__":
    main()
