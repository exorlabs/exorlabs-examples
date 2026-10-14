# Live collector deployment

## 1. Prepare local configuration

Work from the `exor-rackstats` folder. Copy the example files:

```bash
cp .env.nas.example .env.nas
cp .env.proxmox.example .env.proxmox
python3 -c 'import secrets; print(secrets.token_urlsafe(32))'
```

Generate a separate stats token for each service and put it in the corresponding local env file. The real env files, certificates/keys, firmware `config.h` and generated builds are ignored by git.

Create certificates for the actual IPs where the collectors will run:

```bash
python3 tools/make_tls.py --nas-ip 10.0.0.40 --proxmox-collector-ip 10.0.0.50
```

Those are example IPs: replace both. Use the resulting `ca.crt` for the ESP32 and endpoint verifier. Keep private keys and the CA key in `secrets/`. Set `RACKSTATS_UID`/`RACKSTATS_GID` to the owner of these files (`id -u`, `id -g`) so the non-root container can read its own key. Copy the repository and required files privately to each collector machine.

## 2. Synology

Use a new project directory, for example `/volume1/docker/exor-rackstats`. Create its empty `storage-probe` directory on the volume you want to measure. Set `NAS_STORAGE_PROBE` to that exact path.

Set the correct NIC in `.env.nas`. With SSH, `ip -br link` lists interface names. Choose your physical interface or bond; do not choose both members and their bond as separate totals. Temperature is optional and remains `null` until a readable millidegree hwmon file is configured.

From the project directory:

```bash
docker compose --env-file .env.nas -f deploy/compose.nas.yml up -d --build
docker compose --env-file .env.nas -f deploy/compose.nas.yml logs --tail 30
```

The Compose stack uses host networking so `/proc/net/dev` reflects the host NIC. `/proc` and the small storage probe are read-only mounts. It does not require privileged mode, a host PID namespace, access to all NAS shares or the Docker socket. Existing Ghost/Traefik stacks do not participate in this new stack.

Container Manager/Portainer users can create a new project/stack from the supplied Compose file after putting its build context, local env file and secrets at matching paths on the NAS. A pasted Compose file alone cannot build a Dockerfile whose source directory was never uploaded; the SSH command above is the reproducible path.

Verify from a computer that can reach the NAS:

```bash
python3 tools/check_endpoints.py --env .env.nas \
  --url https://10.0.0.40:4300/api/v1/stats --ca-file secrets/ca.crt
```

CPU/network deltas require two samples. Give the service five seconds after startup; an initial `null` is expected, not a zero reading.

## 3. Proxmox API account

In Proxmox, create an enabled service user such as `stats@pve` and a token named `display`, with privilege separation enabled. Give **both the user and token** the `PVEAuditor` role on `/`, with propagation. This example reads the node and VM inventory; it implements no write operations.

The token identifier is `stats@pve!display`. Put the token's actual secret only in `.env.proxmox`. Privilege-separated token permissions are constrained by the backing user's permissions, so granting an ACL to only one of them is insufficient.

Use the selected node's exact name for `PVE_NODE`. Set `PVE_URL` to an HTTPS origin whose hostname/IP matches the PVE certificate. Copy the PVE cluster's public root CA certificate (`/etc/pve/pve-root-ca.pem`) to `secrets/pve-root-ca.pem`. The collector verifies TLS and does not follow redirects with the API token.

Official references: https://pve.proxmox.com/pve-docs/pve-admin-guide.html and https://pve.proxmox.com/pve-docs/api-viewer/ .

## 4. Run the Proxmox collector

A Linux VM/LXC on Proxmox is a suitable collector location. Python 3.10+ is sufficient; the collector does not require packages on the hypervisor.

From the copied repository folder, without Docker:

```bash
PYTHONPATH=server python3 -m rackstats_agent --env .env.proxmox
```

Keep this process running while testing. If you prefer Docker in the VM or on another Linux machine:

```bash
docker compose --env-file .env.proxmox -f deploy/compose.proxmox.yml up -d --build
```

Verify:

```bash
python3 tools/check_endpoints.py --env .env.proxmox \
  --url https://10.0.0.50:4310/api/v1/stats --ca-file secrets/ca.crt
```

Replace the collector IP. It may differ from the PVE API host IP. You can also run the same Python process directly on the host if you choose; the default implementation still uses its read-only HTTPS API for host/VM data.

For a persistent direct Python deployment, `deploy/exor-rackstats.service.example` is a systemd template. Fill the installed source path, a dedicated unprivileged service account and private configuration paths before installing it.

## 5. Connect the ESP32

The ESP32 must reach both collector IPs, normally on the same trusted LAN. Copy the two **stats** tokens and collector URLs into `firmware/config.h`; do not copy the PVE API secret there. Paste the shared collector CA certificate. Configure reachable NTP so certificate date validation succeeds.

Build with `tools/prepare_firmware.py`, compile and upload as described in the README. The screen shows LIVE, STALE, DEMO or OFFLINE; it retains last readings during an outage. A missing sensor uses `--`. Network calls never run inside the LVGL timer/lock.

For an intentional HTTP-only demo, bind `tools/demo_servers.py` to your computer's LAN IP, set the two firmware URLs to that IP and ports 4300/4310, use `local-demo-token`, and set `ALLOW_LAN_HTTP=true`. Keep real collectors in their normal TLS configuration. No router port forwarding is needed.

## Troubleshooting

| Symptom | Check |
| --- | --- |
| 401 from stats service | Stats token in the matching local env file and firmware |
| 503 / unavailable | Correct PVE settings, CA trust, node name, or NAS mounts/permissions |
| PVE returns 401/403 | Token identifier/secret and ACLs for both service user and token |
| Host stats work, VM list unavailable | VM audit permissions and selected node name |
| TLS verification fails | Correct CA, URL matching certificate SAN, and ESP32 time |
| “Missing TLS CA” | Paste `ca.crt` into `STATS_CA_PEM` |
| “Waiting for clock” | Reachable NTP and working Wi-Fi/DNS |
| NAS CPU/network is null initially | Wait for the second collection interval |
| NAS network stays null | Correct interface name and host networking |
| Proxmox network is null | Recent usable RRD samples; older samples are intentionally omitted |
| Port already in use | Choose free collector ports and update URLs; keep existing services running |
| Vendor hash changed | Review the new port before updating the recorded hash |
