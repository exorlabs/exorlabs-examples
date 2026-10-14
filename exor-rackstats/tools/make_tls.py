"""Create a private local CA and two IP-valid collector certs. Requires OpenSSL.
The output directory must not exist; existing private keys are never replaced.
"""
import argparse
import ipaddress
from pathlib import Path
import os
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument("--nas-ip", required=True)
parser.add_argument("--proxmox-collector-ip", required=True)
parser.add_argument("--out", default="secrets")
args = parser.parse_args()
nas = str(ipaddress.ip_address(args.nas_ip))
pve = str(ipaddress.ip_address(args.proxmox_collector_ip))
out = Path(args.out).resolve()
if out.exists(): parser.error("Output exists; choose a new directory instead of replacing certificates")
out.mkdir(parents=True, mode=0o700)
def run(*command):
    subprocess.run(["openssl", *command], cwd=out, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
run("req", "-x509", "-newkey", "rsa:2048", "-nodes", "-sha256", "-days", "3650", "-subj", "/CN=Exor RackStats Local CA",
    "-keyout", "ca.key", "-out", "ca.crt", "-addext", "basicConstraints=critical,CA:TRUE", "-addext", "keyUsage=critical,keyCertSign,cRLSign")
for name, ip in (("nas", nas), ("proxmox", pve)):
    run("req", "-new", "-newkey", "rsa:2048", "-nodes", "-subj", f"/CN={name}-stats", "-keyout", f"{name}.key", "-out", f"{name}.csr")
    extension = out / f"{name}.ext"
    extension.write_text(f"subjectAltName=IP:{ip},DNS:localhost\nbasicConstraints=CA:FALSE\nkeyUsage=digitalSignature,keyEncipherment\nextendedKeyUsage=serverAuth\n")
    run("x509", "-req", "-in", f"{name}.csr", "-CA", "ca.crt", "-CAkey", "ca.key", "-CAcreateserial", "-out", f"{name}.crt",
        "-days", "825", "-sha256", "-extfile", str(extension))
for key in out.glob("*.key"): os.chmod(key, 0o600)
for cert in out.glob("*.crt"): os.chmod(cert, 0o644)
print(f"Certificates created in {out}. Put ca.crt in the ESP32 config and endpoint checks. Keep all keys private.")
