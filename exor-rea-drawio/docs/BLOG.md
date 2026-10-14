# Opening a draw.io file without draw.io

Most of us open a diagram, move a few boxes around and save it without thinking much about the file underneath. That changes when we want to do something outside the editor—list the names of our servers, compare two versions, or check that a backup still contains the diagram data.

draw.io looks like a good place to start. Its files are XML. Surely the labels and connections should be sitting there, ready to read.

Then you open a compressed `.drawio` file and find something like this inside a page:

```text
7ZxZd6M2FIB/jc9pH5LDjv3oLZnTSdJpnXbaRxlkQwKIgpzY8+srgVglvGDH...
```

The page has a perfectly readable name. Its contents look nothing like a diagram.

That is our starting point. We are going to follow this string back into draw.io, find out what happens to it, and recover the XML with a small independent tool.

## The first clue only gets us halfway

For a repeatable example, use the C4 diagram from [draw.io's own examples repository](https://github.com/jgraph/drawio-diagrams). It contains four pages: Context, Container, Component and Class. The [companion project](https://github.com/exorlabs/exorlabs-examples/tree/main/exor-rea-drawio) downloads that file and a pinned version of draw.io's published application bundle.

The string looks like Base64. Decoding it is a reasonable first move, but the result is still not XML. We get binary bytes.

That tells us something useful: Base64 was an outer layer. Removing it did not reveal the whole format.

Compression is the next thing to check. Try ordinary zlib decompression on this example and it reports an incorrect header. It would be easy to conclude that the file is corrupt. But there is another possibility: we chose the wrong kind of decompression.

## Follow the string back into draw.io

This is where [REA](https://github.com/morluto/rea) fits into the investigation. With REA connected to your coding agent, give it a question tied to the file we can actually see:

> In this draw.io application, what happens to the text inside a compressed diagram page before it becomes the XML model? Follow that path and show me the code behind each step.

The useful answer needs more than “it is Base64.” It needs to lead us through the application and explain the remaining transformations. The repository includes the longer investigation prompt and the command for analyzing the downloaded artifacts.

In the published bundle, the relevant functions are `Graph.compress` and `Graph.decompress`. The decoder uses `inflateRaw`. That word *Raw* explains the header error: these bytes are a raw DEFLATE stream, rather than the wrapped stream that the usual zlib call expects.

After inflating them, we are much closer. The beginning now looks like:

```text
%3CmxGraphModel%20...
```

That is recognisable text, but the angle brackets and spaces are still percent-encoded. One more decoding step gives us `<mxGraphModel ...>` and the cells that describe the page.

The path back is Base64 decoding, raw DEFLATE decompression, then URL decoding. Three ordinary operations, in a particular order. Each clue explained why the previous attempt had stopped short.

## Turn the discovery into something useful

The core Python translation is small:

```python
raw = base64.b64decode(payload)
escaped_xml = zlib.decompress(raw, wbits=-15).decode("utf-8")
xml = urllib.parse.unquote(escaped_xml)
```

The full utility handles the surrounding file too: all its pages, page names and IDs, and files that already contain uncompressed XML. It writes a new `.drawio` file and leaves the original alone.

From the companion project's `exor-rea-drawio` folder, run:

```bash
node tools/fetch_upstream.mjs
python3 drawio_unpack.py upstream/examples/C4.drawio --out artifacts/C4-readable.drawio
python3 scripts/compare_with_app.py
```

The C4 file produces four readable pages, containing 24, 31, 36 and 26 cells respectively. Those cells carry the information we were looking for: labels, styles, positions and references connecting one cell to another.

Getting readable output is encouraging. Checking it against the application is stronger evidence. The comparison script runs the unchanged codec functions from draw.io's verified bundle, using its real compression dependency. Our decoder agrees with it on ten pages from three official diagrams. A further hundred cases check both directions, including Unicode labels, percent signs and literal plus signs.

That last detail matters. URL decoding is easy to mix up with form decoding, where a plus sign can become a space. A diagram labelled `NAS + Proxmox` should keep its plus sign.

We now have a way to read diagram data from a script without opening every file in the editor. From there, listing equipment names, inspecting connections or checking a folder of diagrams becomes a normal XML-processing task.

draw.io also [documents the format](https://www.drawio.com/docs/reference/diagram-generation/), which gives us another way to check the interpretation. The companion repository contains the full code and a validation note recording which checks have been completed, including the REA and browser checks still pending.
