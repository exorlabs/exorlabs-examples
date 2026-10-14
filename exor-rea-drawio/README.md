# Open a draw.io file without draw.io

Investigate how the real [draw.io application](https://github.com/jgraph/drawio) stores a diagram, then unpack its files with an independent Python implementation.

The target is draw.io's published application bundle. It is downloaded unchanged from the official repository at a pinned commit. The example diagrams come from the official `jgraph/drawio-diagrams` repository. We did not create a fake application for this investigation.

## Run the working example

Use Python 3.10+ and Node.js 24.11+ or a supported newer runtime. No Python packages or project npm dependencies are needed.

From this directory:

```bash
node tools/fetch_upstream.mjs
python3 drawio_unpack.py upstream/examples/C4.drawio --out artifacts/C4-uncompressed.drawio
python3 scripts/compare_with_app.py
python3 -m unittest discover -s tests -v
```

The first command downloads the real application files and three official diagrams, checking their recorded SHA-256 digests. The unpacking command produces four readable pages:

```text
C4 Context: 24 cells
C4 Container: 31 cells
C4 Component: 36 cells
C4 Class: 26 cells
```

The result is an uncompressed `.drawio` file. It preserves the page IDs, names, cell data and file metadata. XML formatting and attribute order may change during serialization. Output files must be new; the utility refuses to overwrite an existing file.

To try your own file, save/export a `.drawio` or XML file from [draw.io](https://app.diagrams.net/) and pass its path to the same command. Open the resulting `.drawio` file through draw.io's File → Open From → Device to check your diagram visually. That reader-side UI check is separate from the automated codec checks below.

## Investigate it with REA

If REA is already connected to your coding agent, use [docs/INVESTIGATION.md](docs/INVESTIGATION.md). The question is specific: what happens to the text inside a compressed `<diagram>` element before it becomes a graph model?

The CLI preparation command is:

```bash
npm install --global rea-agents@6.4.0
python3 scripts/run_rea.py
```

The wrapper analyzes the actual downloaded artifacts in `upstream/drawio`; it saves genuine REA output or fails. It does not claim that a failed preflight is a successful investigation. The downloaded directory contains the published bundle plus its corresponding source and codec dependency; it is a focused artifact collection, not an offline installation of the entire draw.io UI.

REA can organize and trace the application evidence. The coding agent still interprets it and writes the independent implementation. The comparison command checks that interpretation against real application functions.

The REA command completed successfully on GitHub's Ubuntu runner on October 14, 2026. Its [actual analysis report](https://github.com/exorlabs/exorlabs-examples/actions/runs/38656611840/artifacts/11937181785) is available as a workflow artifact. This is a static analysis of the four downloaded JavaScript files; browser rendering and interactive feature tracing are separate checks.

## What the checks establish

`scripts/compare_with_app.py` extracts four unchanged codec function definitions from the hash-verified application bundle and loads its real bundled pako dependency. The native harness does not reimplement those compression functions. It compares:

- Ten pages from three official example files with draw.io's decoder.
- One hundred cases produced by the real app's encoder with our Python decoder.
- Those same hundred cases produced by our Python encoder with the real app's decoder.

This exercises the real application component in both directions. It does not start the full browser application, render diagrams or run every draw.io feature. The decoder call uses the application's `checked=true` option to return decoded XML before its control-character cleanup; test inputs are valid graph-model XML.

Seven local tests also cover multi-page metadata, plain XML pages, Unicode/plus signs, invalid data and retained file-level children. See the root `VALIDATION.md` for the exact checks and REA/runtime limits.

## Repository structure

| Path | Purpose |
| --- | --- |
| `drawio_unpack.py` | Complete independent decoder and CLI |
| `tools/fetch_upstream.mjs` | Downloads actual upstream artifacts; verifies their digests |
| `tools/application_codec.mjs` | Runs unchanged codec functions from the real bundle |
| `scripts/compare_with_app.py` | Cross-checks official files and both encoder/decoder directions |
| `scripts/run_rea.py` | Genuine REA CLI operation |
| `tests/` | Focused decoder/file tests |
| `docs/INVESTIGATION.md` | Reader's investigation prompt and evidence trail |
| `docs/BLOG.md` | Narrative article for Ghost |
| `upstream-manifest.json` | Exact artifact versions, paths and SHA-256 values |

Downloaded upstream files and generated output are ignored by git and excluded from the release ZIP. Upstream licenses remain with their projects. The manifest downloads draw.io's Apache license alongside its code.
