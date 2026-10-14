# Validation of the supplied examples

These results describe the source supplied in this repository. They distinguish a running program or a successful build from a deployment on a private service or physical board.

## Real draw.io application investigation

The target is draw.io's published 32.4.1 bundle from official commit `9034053fba80a435e27d68d374bc564b83917ae9`. Its corresponding source and pako dependency are downloaded unchanged, with SHA-256 checks. Three diagrams come from official `jgraph/drawio-diagrams` commit `60b4bc39c6fcc0df88d5ad3f86aa98bd6a3fa0c7`. Neither the target application nor those example diagrams were invented for this project.

| Check | Result |
| --- | --- |
| Upstream fetch script | Pinned artifacts verified; clean release extraction is used to check actual downloading |
| Decoder on the official C4 file | Four pages recovered: 24, 31, 36 and 26 cells |
| Official example comparison | Passed: ten pages across three files agree with draw.io's actual decoder |
| App-encoder → Python-decoder | Passed: 100 cases, including Unicode, percent and plus signs |
| Python-encoder → app-decoder | Passed: the same 100 cases return the original model XML |
| Local decoder/file suite | Passed: seven tests covering metadata, multiple pages, plain XML, Unicode, invalid data and retained file-level children |
| Node/Python syntax checks | Passed |
| Real REA 6.4.0 analysis of the draw.io artifacts | Attempted; stopped during source analysis because the authoring runtime cannot satisfy its procps process-ownership preflight |

The application comparison extracts four unchanged codec function definitions from the digest-verified bundle and uses the application's real pako dependency. It does not substitute a homemade codec as the oracle. The decoder call uses `Graph.decompress(payload, false, true)` to obtain decoded text before the UI's control-character cleanup. Inputs are valid graph-model XML. This is an application-component test, not a full browser run.

The cloud browser timed out opening draw.io. No observed editor rendering, successful UI save/import, screenshot or full browser round trip is claimed. The README describes the first visual check readers can run with their own files in the actual editor. XML may be reformatted during output; page IDs, names, model data and other file metadata are retained.

REA emitted `capability_unavailable` / `unsupported_provider`: `ps -axo pid=,ppid=,pgid=,uid=,stat=,command=` failed with `fatal library error, lookup self`. Its partial observation is not a completed feature trace. No REA guard was modified. The unmodified CLI operation and a strict Ubuntu CI job are included; the real command must succeed on a normal host before its results are used as a completed REA case study.

The blog follows findings checked against the actual bundle and examples. It does not invent a first-person browser session, a successful REA trace or a secret/undocumented format. draw.io publishes its format documentation too.

## Stats services and decoder

| Check | Result |
| --- | --- |
| Python server suite | Passed: 11 tests, including actual HTTP authorization, verified HTTPS, rejection of an untrusted certificate, collector normalization and stale/unavailable snapshots |
| Two running demo services + `tools/check_endpoints.py --demo` | Passed: both HTTP endpoints returned the shared contract; their data is explicitly simulated |
| Firmware's actual ArduinoJson decoder, compiled with `-Wall -Wextra -Werror` | Passed: decoded payloads from the running HTTP services, preserved unknown values, accepted a stale snapshot and rejected an invalid schema |
| Linux collector against the authoring host's `/proc` and filesystem | Executed successfully; this is not a Synology deployment |
| Proxmox collector requests | Tested against a local API fixture implementing the selected node, VM inventory and RRD endpoints with token checks |
| Compose and workflow YAML | Parsed successfully; no Docker engine was available for a built-container run |

The fixtures do not impersonate a private NAS or Proxmox installation. The real collectors are included, with HTTPS, local configuration templates, TLS tooling and deployment instructions. Their first deployment still needs your hosts, addresses, permissions and tokens.

## Complete ESP32 firmware

The final sketch, including Wi-Fi, TLS, HTTP polling, JSON parsing, the snapshot queue and LVGL UI, compiled successfully for the Waveshare ESP32-S3-LCD-3.16 using:

- Espressif Arduino core **3.1.0**
- Vendor-matched LVGL **9.3.0**
- ArduinoJson **7.3.1**
- FQBN `esp32:esp32:esp32s3:PSRAM=opi,FlashSize=16M,PartitionScheme=app3M_fat9M_16MB,USBMode=hwcdc,CDCOnBoot=cdc`

The final compile reports **1,231,560 bytes** of program storage (39% of the selected application partition) and **112,448 bytes** of static dynamic-memory use (34%). Static figures do not establish peak runtime heap or PSRAM use. The vendor toolchain emitted a linker warning about `crtn.o` lacking `.note.GNU-stack`; the build completed successfully.

The preparation script was run against the official vendor archive. It checks the reviewed display-port SHA-256 before inserting the UI inside the existing locked creation site. Vendor sources and libraries are downloaded separately and are not redistributed in this repository.

The same UI module was linked to the real LVGL 9.3.0 implementation and rendered at 820×320 and 320×820. Rendered data came from the running HTTP demo services. All six direct screen objects stayed within bounds, and 60 simulated one-second updates per render exercised page switching and stale aging without increasing the root object count. The included preview is this actual LVGL render, not a board photograph.

No physical ESP32 upload, panel/PSRAM reliability run, private NAS Docker deployment or authenticated private PVE deployment is claimed. Use `exor-rackstats/docs/DEPLOYMENT.md` and the firmware README for those first local checks.

## Release and publishing

The public package contains source, tests, deployment files, templates, an MIT license, short blog bodies and four CI jobs. Real credentials, certificate private keys, generated builds, vendor downloads and authoring QA files are excluded. The final ZIP is checked by extraction, fresh upstream downloads and the packaged application-codec comparison.

The GitHub workflow has not been executed on a remote repository yet. Its results become available after the first push. The companion article links are set to the intended public repository, `https://github.com/exorlabs/exorlabs-examples`.
