# Exor Labs technical examples

Two companion projects for the Exor Labs technical blog.

## Get the code

```bash
git clone https://github.com/exorlabs/exorlabs-examples.git
cd exorlabs-examples
```

| Project | Start here | What you can run |
| --- | --- | --- |
| Investigate draw.io with REA | [exor-rea-drawio/README.md](exor-rea-drawio/README.md) | Download the real app and official diagrams, unpack their page data and compare with the application's codec |
| ESP32 infrastructure display | [exor-rackstats/README.md](exor-rackstats/README.md) | NAS/PVE stats services, endpoint checks and complete Arduino/LVGL firmware |

The two projects run independently. Start with the ESP32 project's API demo if you want to try the dashboard services without hardware. Its [deployment guide](exor-rackstats/docs/DEPLOYMENT.md) covers the real NAS and Proxmox collectors.

| Folder | Contents |
| --- | --- |
| `exor-rea-drawio/` | Decoder, real-app comparison, REA runner, tests and investigation guide |
| `exor-rackstats/firmware/` | Arduino sketch, networking, JSON parser and LVGL interface |
| `exor-rackstats/server/` | NAS and Proxmox collector services |
| `exor-rackstats/deploy/` | Docker Compose stacks and systemd example |
| `exor-rackstats/tools/` | Demo servers, endpoint checks, TLS setup and sketch preparation |
| `exor-rackstats/tests/` | Collector, authorization and TLS tests |
| `.github/workflows/` | Automated example checks and ESP32 compilation |

## First example: a real application

```bash
cd exor-rea-drawio
node tools/fetch_upstream.mjs
python3 drawio_unpack.py upstream/examples/C4.drawio --out artifacts/C4-readable.drawio
python3 scripts/compare_with_app.py
python3 -m unittest discover -s tests -v
```

The download pins draw.io 32.4.1 and official example files by commit and SHA-256. The comparison runs unchanged codec functions from the published application bundle. For an investigation with your REA-connected agent, follow `docs/INVESTIGATION.md` in the project.

The independent Python utility is the outcome of investigating the file format. The application under investigation is draw.io.

## Second example: connected LVGL dashboard

From `exor-rackstats`, terminal 1:

```bash
python3 tools/demo_servers.py
```

Terminal 2, in the same folder:

```bash
python3 tools/check_endpoints.py --demo
python3 -m unittest discover -s tests -v
```

The first-run demo data is explicitly simulated. Use the deployment guide for real Synology/Proxmox collection and the firmware README to build/upload the board.

## GitHub and publishing

The public repository is [exorlabs/exorlabs-examples](https://github.com/exorlabs/exorlabs-examples). [GITHUB-SETUP.md](GITHUB-SETUP.md) covers the initial upload and later updates. Four workflow jobs check the real application codec, REA analysis, collectors/decoder and firmware compilation. The REA job retains the actual analysis/error JSON as a downloadable artifact; it stays failed if the real CLI operation fails. See [GitHub Actions](https://github.com/exorlabs/exorlabs-examples/actions) for the current results.

Each project's `docs/BLOG.md` is a short article with full-code links to its folder in this repository.

The first article follows the clues in the saved diagram. REA's static analysis has also completed on GitHub's Ubuntu runner; its report is available from the workflow artifact. See [VALIDATION.md](VALIDATION.md) for the evidence, the earlier authoring-runtime limitation and the remaining browser and hardware/private-host deployment checks.

Downloaded upstream files, generated outputs, real `.env` files, `firmware/config.h`, certificates/keys and build products are ignored. Original companion code is MIT licensed. draw.io and the other separately obtained dependencies retain their upstream licenses.
