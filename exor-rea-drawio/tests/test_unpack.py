import unittest
import xml.etree.ElementTree as ET
from drawio_unpack import DiagramError, decode_page_text, encode_page_text, unpack_document, summarize

MODEL = '<mxGraphModel><root><mxCell id="0"/><mxCell id="1" parent="0"/><mxCell id="2" parent="1" vertex="1" value="NAS + Montréal 😀 &amp; 50%"/></root></mxGraphModel>'


class UnpackTests(unittest.TestCase):
    def test_unicode_and_literal_plus_round_trip(self):
        self.assertEqual(decode_page_text(encode_page_text(MODEL)), MODEL)

    def test_multiple_pages_and_metadata_preserved(self):
        text = f'<mxfile version="test" custom="keep"><diagram id="a" name="NAS">{encode_page_text(MODEL)}</diagram><diagram id="b" name="PVE">{encode_page_text(MODEL)}</diagram></mxfile>'
        root = unpack_document(text)
        self.assertEqual(root.get("custom"), "keep")
        self.assertEqual([(p.get("id"), p.get("name")) for p in root], [("a", "NAS"), ("b", "PVE")])
        self.assertEqual([p["cells"] for p in summarize(root)], [3, 3])
        self.assertEqual(root.get("compressed"), "false")

    def test_plain_page_does_not_need_decompression(self):
        root = unpack_document(f'<mxfile><diagram name="plain">{MODEL}</diagram></mxfile>')
        self.assertEqual(root.find('.//mxCell[@id="2"]').get("value"), "NAS + Montréal 😀 & 50%")

    def test_bare_graph_model_is_wrapped(self):
        self.assertEqual(unpack_document(MODEL).find("diagram").get("name"), "Page-1")

    def test_invalid_payloads_fail(self):
        for value in ("not-base64!", "", "YWJj"):
            with self.subTest(value=value), self.assertRaises(DiagramError): decode_page_text(value)

    def test_wrong_document_and_page_are_rejected(self):
        for text in ("<other/>", "<mxfile/>", "<mxfile><diagram><other/></diagram></mxfile>"):
            with self.subTest(text=text), self.assertRaises(DiagramError): unpack_document(text)

    def test_file_metadata_child_is_retained(self):
        root = unpack_document(f'<mxfile><mxAtlasLibraries/><diagram>{encode_page_text(MODEL)}</diagram></mxfile>')
        self.assertIsNotNone(root.find("mxAtlasLibraries"))


if __name__ == "__main__": unittest.main()
