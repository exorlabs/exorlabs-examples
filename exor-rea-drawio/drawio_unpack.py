"""Unpack draw.io's page payloads into an editable, uncompressed .drawio file."""
import argparse
import base64
import binascii
import copy
import json
from pathlib import Path
import re
import sys
from urllib.parse import quote, unquote_to_bytes
import xml.etree.ElementTree as ET
import zlib

MAX_INPUT = 32 * 1024 * 1024
MAX_PAGE = 16 * 1024 * 1024
MAX_TOTAL = 64 * 1024 * 1024


class DiagramError(ValueError):
    pass


def parse_xml(text):
    if re.search(r"<!\s*(?:DOCTYPE|ENTITY)\b", text, re.IGNORECASE):
        raise DiagramError("DTD/entity declarations are outside this file-format example")
    try:
        return ET.fromstring(text)
    except ET.ParseError as exc:
        raise DiagramError(f"Invalid diagram XML: {exc}") from exc


def decode_page_text(payload):
    try:
        compressed = base64.b64decode("".join(payload.split()), validate=True)
    except (binascii.Error, ValueError) as exc:
        raise DiagramError("Page payload is not valid Base64") from exc
    try:
        inflater = zlib.decompressobj(wbits=-15)
        encoded = inflater.decompress(compressed, MAX_PAGE + 1)
        if len(encoded) > MAX_PAGE or inflater.unconsumed_tail:
            raise DiagramError("Decoded page exceeds the size limit")
        if not inflater.eof or inflater.unused_data:
            raise DiagramError("Page has an incomplete or trailing DEFLATE stream")
        uri_text = encoded.decode("utf-8", errors="strict")
        if re.search(r"%(?![0-9A-Fa-f]{2})", uri_text):
            raise DiagramError("Malformed percent escape in the decoded page")
        xml = unquote_to_bytes(uri_text).decode("utf-8", errors="strict")
    except (zlib.error, UnicodeError) as exc:
        raise DiagramError(f"Page decoding failed: {exc}") from exc
    if parse_xml(xml).tag != "mxGraphModel":
        raise DiagramError("Decoded page is not an mxGraphModel")
    return xml


def encode_page_text(xml):
    """Independent encoder used for cross-checking with the real app's decoder."""
    if parse_xml(xml).tag != "mxGraphModel":
        raise DiagramError("Expected an mxGraphModel")
    encoded = quote(xml, safe="-_.!~*'()").encode("ascii")
    compressor = zlib.compressobj(wbits=-15)
    compressed = compressor.compress(encoded) + compressor.flush()
    return base64.b64encode(compressed).decode("ascii")


def unpack_document(text):
    if len(text.encode("utf-8")) > MAX_INPUT:
        raise DiagramError("Input exceeds the size limit")
    source = parse_xml(text)
    if source.tag == "mxGraphModel":
        result = ET.Element("mxfile")
        page = ET.SubElement(result, "diagram", {"name": "Page-1"})
        page.append(copy.deepcopy(source))
        return result
    if source.tag != "mxfile":
        raise DiagramError("Expected an mxfile or mxGraphModel XML document")
    result = copy.deepcopy(source)
    pages = result.findall("diagram")
    if not pages:
        raise DiagramError("File contains no diagram pages")
    total = 0
    for page in pages:
        children = list(page)
        if children:
            if len(children) != 1 or children[0].tag != "mxGraphModel":
                raise DiagramError("Uncompressed page must contain one mxGraphModel")
            model = children[0]
        else:
            if not (page.text or "").strip():
                raise DiagramError("Empty diagram page")
            model = parse_xml(decode_page_text(page.text))
            page.text = None
            page.append(model)
        total += len(ET.tostring(model, encoding="utf-8"))
        if total > MAX_TOTAL:
            raise DiagramError("Total decoded diagram exceeds the size limit")
    result.set("compressed", "false")
    return result


def summarize(root):
    summaries = []
    for page in root.findall("diagram"):
        model = page.find("mxGraphModel")
        cells = model.findall(".//mxCell")
        labels = []
        for node in model.iter():
            label = node.get("label") or node.get("value")
            if label:
                labels.append(label)
        summaries.append({"name": page.get("name", ""), "id": page.get("id"),
                          "cells": len(cells), "vertices": sum(c.get("vertex") == "1" for c in cells),
                          "edges": sum(c.get("edge") == "1" for c in cells), "labels": labels})
    return summaries


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("file", type=Path)
    parser.add_argument("--out", type=Path, required=True, help="New uncompressed .drawio file")
    parser.add_argument("--json", action="store_true", help="Also print page counts and stored labels")
    args = parser.parse_args()
    try:
        if args.file.stat().st_size > MAX_INPUT:
            raise DiagramError("Input exceeds the size limit")
        root = unpack_document(args.file.read_text(encoding="utf-8-sig"))
        args.out.parent.mkdir(parents=True, exist_ok=True)
        with args.out.open("xb") as stream:
            ET.ElementTree(root).write(stream, encoding="utf-8", xml_declaration=True)
        pages = summarize(root)
        print(f"Decoded {len(pages)} pages -> {args.out}")
        for page in pages:
            print(f"  {page['name']}: {page['cells']} cells ({page['vertices']} shapes, {page['edges']} connections)")
        if args.json:
            print(json.dumps(pages, indent=2, ensure_ascii=False))
    except (OSError, UnicodeError, DiagramError) as exc:
        parser.exit(1, f"Error: {exc}\n")


if __name__ == "__main__":
    main()
