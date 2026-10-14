# From Proxmox and Synology stats to an ESP32 dashboard

A physical infrastructure dashboard connects three different jobs: collecting trustworthy measurements, transporting a snapshot and drawing it without blocking the display.

This project implements all three. Two Python services collect Proxmox and Synology metrics, and an ESP32-S3 fetches their JSON snapshots for an LVGL 9 dashboard. The [full companion repository](https://github.com/exorlabs/exorlabs-examples/tree/main/exor-rackstats) contains the server code, deployment files, Arduino firmware and tests.

The display uses the Waveshare ESP32-S3-LCD-3.16 development board. It alternates NAS and Proxmox pages every ten seconds and shows CPU, memory, filesystem usage, network rates and available temperature/VM information. It is a development example, rather than a finished Exor Labs product.

## Give both sources one contract

The Proxmox collector reads its HTTPS API with a read-only token. It collects the selected node's status, VM inventory and recent RRD network averages. The Synology collector reads host Linux counters and filesystem capacity from a container with read-only mounts.

Both expose `/api/v1/stats`. Their shared envelope includes:

```json
{
  "schema_version": 1,
  "source": "nas",
  "state": "fresh",
  "age_seconds": 0.4,
  "host": {
    "name": "Synology",
    "cpu_percent": 18.0,
    "memory": {"percent": 37.5},
    "storage": {"percent": 33.3}
  }
}
```

This abbreviated example shows the fields used by the main cards. The actual response also includes byte totals, uptime, network measurements, optional temperature, VM information and warnings.

A missing measurement is `null`. It must not become a reassuring zero on the screen.

## Understand where the measurements come from

| Measurement | NAS source | Proxmox source |
| --- | --- | --- |
| CPU | Difference between successive `/proc/stat` samples | Node API's CPU fraction, converted to percent |
| Memory | Total minus `MemAvailable` | Node API's used/total memory |
| Filesystem | `statvfs` of a probe directory on the selected volume | Node root-filesystem used/total |
| Network | Byte-counter difference for one configured interface | Recent RRD averages |
| VMs | Not collected by the NAS agent | Accessible VMs/LXCs on the selected node |

CPU and network counter deltas need two NAS samples. Initial unknown values are expected. Counter resets also produce unknown values for that interval, rather than a negative transfer rate.

For a bond or USB NIC, configure the correct interface explicitly. Summing a bond and its member interfaces can count the same traffic more than once. Similarly, the Proxmox filesystem card is a root-filesystem measurement, not the combined capacity of every storage pool.

## Try the servers first

From the companion project's `exor-rackstats` directory, start the deliberately simulated first-run mode:

```bash
python3 tools/demo_servers.py
```

In another terminal:

```bash
python3 tools/check_endpoints.py --demo
python3 -m unittest discover -s tests -v
```

This checks the API contract before hardware is involved. The supplied deployment guide then switches to the real collectors: a Synology Container Manager/Portainer service and a Proxmox API collector running in a Linux VM/LXC or Python process.

The services require a stats bearer token and support HTTPS. The PVE API credential stays on its collector; the ESP32 receives only the tokens for reading the resulting snapshots. Certificate generation and verification steps are included in the repository.

## Keep network polling out of the LVGL task

The Arduino firmware uses a network task to fetch and decode both sources. It puts the latest complete pair into a single-slot FreeRTOS queue:

```cpp
xQueueOverwrite(snapshots, &current);
```

The LVGL timer takes the latest pair without waiting:

```cpp
xQueueReceive(snapshots, pair, 0);
```

It updates existing labels and bars instead of rebuilding the screen. The vendor port remains responsible for the LVGL mutex, tick and rendering task. A slow HTTP request can delay the next measurement while the screen continues updating its age and connection state.

If collection or transport fails, the last valid numbers remain visible and the page becomes STALE. Without any valid reading it shows OFFLINE and `--`. The UI also marks simulated data as DEMO.

## Build the board-specific sketch

Copy `firmware/config.h.example` to a local `config.h` and fill the Wi-Fi settings, collector URLs, stats tokens and CA certificate. Then use the official Waveshare demo ZIP:

```bash
python3 tools/prepare_firmware.py /path/to/ESP32-S3-LCD-3.16-Demo.zip
```

The script creates a complete Arduino sketch with the reviewed display driver and matching LVGL configuration. It inserts UI creation inside the port's existing lock and disables its backlight demonstration.

The tested dependency set is Espressif Arduino core 3.1.0, LVGL 9.3.0 and ArduinoJson 7.3.1. The README includes the exact compile command, PSRAM/flash settings and local upload steps. HTTPS also requires a valid device clock, so configure reachable NTP rather than bypassing certificate validation.

## Test the boundaries between components

The Python tests cover collector normalization, authentication, stale snapshots and certificate verification. A native build of the firmware's actual C++ JSON decoder receives HTTP server payloads, including `null` values and invalid schema versions. The complete ESP32 sketch also has a compilation job.

Those checks establish useful compatibility between the components. The first upload still needs a real board and your configured private services. The project does not claim a device deployment or NAS/PVE credentials it has never used.

Keeping those boundaries explicit makes the design easier to extend: change a collector without rewriting the UI, add a measurement to the contract, and keep an unavailable source from freezing or misleading the display.
