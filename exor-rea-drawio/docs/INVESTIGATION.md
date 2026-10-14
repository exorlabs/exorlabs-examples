# Follow the diagram back into the application

Start with the downloaded `upstream/examples/C4.drawio`. Open it in a text editor. Its four `<diagram>` elements contain encoded text, even though the application displays meaningful shapes and relationships.

For the investigation, leave `drawio_unpack.py` and `scripts/compare_with_app.py` closed until you have a hypothesis. The application artifacts in `upstream/drawio` are the actual target.

Use this prompt with your REA-equipped agent:

> Investigate the downloaded draw.io application in `upstream/drawio`. Explain how the text inside a compressed `<diagram>` element becomes the XML model that the editor consumes. Use REA to analyze the application artifacts and trace the relevant data flow. Start from file loading and the literals `<diagram>` and `mxGraphModel`; narrow the investigation to the page decoder. Report the actual files and functions supporting each conclusion, and distinguish inspected code from observed execution. Do not use the companion Python implementation or its comparison script as the source of the answer. Do not claim that an absent edge proves a feature does not exist. If REA is unavailable, report that directly. After you have explained the transformations and their order, implement a small independent decoder and check it against a real downloaded diagram. Then compare your findings with the companion implementation.

## Clues you can check yourself

1. `<mxfile>` and page names are readable; the page content is encoded.
2. Base64 decoding yields bytes, not the graph's XML.
3. Ordinary zlib decompression and raw DEFLATE are different operations.
4. The inflated text still contains percent escapes.
5. After the final decoding step, the model contains cell IDs, values, styles, geometry and edge references.

Only consult the following locations after investigating: the published bundle contains `Graph.compress` and `Graph.decompress`; corresponding source is in `Graph.js`. `Editor.js` includes `Editor.extractGraphModel`, which leads into the decoded model. The source and bundle are the same pinned application version, but the application graph may report ambiguity from duplicated source/bundle symbols; use artifact locations when selecting a node.

## Practical follow-up

Decode all pages, preserving names and IDs. Try an already uncompressed file. Try Unicode labels and a literal plus sign. Compare the XML returned by your implementation with the real application's decoder; compare model content rather than requiring two compression libraries to generate identical compressed bytes.

The existing file format is documented by draw.io. This is a guided investigation of a real application, not a claim to have discovered a secret format. REA is one way to navigate the application evidence; the official format documentation provides an additional check.
