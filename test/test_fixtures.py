"""test/test_fixtures.py — Live tests with real fixture files. No mocks, no model inference.

These tests verify that the 2md tools correctly parse, extract metadata from,
and convert real files without requiring any ML model to be loaded. Each test
class is skipped if the corresponding fixture file is missing — run
test/create_fixtures.py first to generate them.

Run:
    python -m pytest test/test_fixtures.py -v
"""

import sys
import tempfile
import unittest
from pathlib import Path

FIXTURES = Path(__file__).parent / "fixtures"
sys.path.insert(0, str(Path(__file__).parent.parent))  # add project root


def fixture_exists(name: str) -> bool:
    """Return True if a named fixture file exists in test/fixtures/."""
    return (FIXTURES / name).exists()


# ---------------------------------------------------------------------------
# TestDocFixture — doc2md.py with real DOCX/PPTX/XLSX files
# ---------------------------------------------------------------------------

class TestDocFixture(unittest.TestCase):
    """doc2md.py with real fixture documents (no model inference)."""

    @unittest.skipUnless(fixture_exists("sample.docx"), "sample.docx fixture missing")
    def test_docx_reads_without_error(self):
        from doc2md import convert_document
        path = FIXTURES / "sample.docx"
        result = convert_document(path)
        self.assertIsInstance(result, str)
        self.assertGreater(len(result), 10)

    @unittest.skipUnless(fixture_exists("sample.docx"), "sample.docx fixture missing")
    def test_docx_content_has_paragraph(self):
        from doc2md import convert_document
        path = FIXTURES / "sample.docx"
        result = convert_document(path)
        self.assertIn("test paragraph", result.lower())

    @unittest.skipUnless(fixture_exists("sample.docx"), "sample.docx fixture missing")
    def test_docx_metadata_has_title(self):
        from doc2md import extract_doc_metadata
        path = FIXTURES / "sample.docx"
        meta = extract_doc_metadata(path, "docx")
        self.assertEqual(meta.get("title"), "Test Document")

    @unittest.skipUnless(fixture_exists("sample.docx"), "sample.docx fixture missing")
    def test_docx_metadata_has_author(self):
        from doc2md import extract_doc_metadata
        path = FIXTURES / "sample.docx"
        meta = extract_doc_metadata(path, "docx")
        self.assertEqual(meta.get("author"), "Test Author")

    @unittest.skipUnless(fixture_exists("sample.docx"), "sample.docx fixture missing")
    def test_docx_metadata_has_format(self):
        from doc2md import extract_doc_metadata
        path = FIXTURES / "sample.docx"
        meta = extract_doc_metadata(path, "docx")
        self.assertEqual(meta.get("format"), "docx")

    @unittest.skipUnless(fixture_exists("sample.pptx"), "sample.pptx fixture missing")
    def test_pptx_reads_without_error(self):
        from doc2md import convert_document
        path = FIXTURES / "sample.pptx"
        result = convert_document(path)
        self.assertIsInstance(result, str)
        self.assertGreater(len(result), 5)

    @unittest.skipUnless(fixture_exists("sample.pptx"), "sample.pptx fixture missing")
    def test_pptx_metadata_has_slides_count(self):
        from doc2md import extract_doc_metadata
        path = FIXTURES / "sample.pptx"
        meta = extract_doc_metadata(path, "pptx")
        self.assertIn("slides", meta)
        self.assertEqual(meta["slides"], 2)

    @unittest.skipUnless(fixture_exists("sample.pptx"), "sample.pptx fixture missing")
    def test_pptx_metadata_has_author(self):
        from doc2md import extract_doc_metadata
        path = FIXTURES / "sample.pptx"
        meta = extract_doc_metadata(path, "pptx")
        self.assertEqual(meta.get("author"), "Test Author")

    @unittest.skipUnless(fixture_exists("sample.xlsx"), "sample.xlsx fixture missing")
    def test_xlsx_reads_without_error(self):
        from doc2md import convert_document
        path = FIXTURES / "sample.xlsx"
        result = convert_document(path)
        self.assertIsInstance(result, str)

    @unittest.skipUnless(fixture_exists("sample.xlsx"), "sample.xlsx fixture missing")
    def test_xlsx_metadata_has_sheets(self):
        from doc2md import extract_doc_metadata
        path = FIXTURES / "sample.xlsx"
        meta = extract_doc_metadata(path, "xlsx")
        self.assertIn("sheets", meta)
        self.assertGreaterEqual(meta["sheets"], 1)

    @unittest.skipUnless(fixture_exists("sample.xlsx"), "sample.xlsx fixture missing")
    def test_xlsx_metadata_has_title(self):
        from doc2md import extract_doc_metadata
        path = FIXTURES / "sample.xlsx"
        meta = extract_doc_metadata(path, "xlsx")
        self.assertEqual(meta.get("title"), "Test Workbook")

    @unittest.skipUnless(fixture_exists("sample.xlsx"), "sample.xlsx fixture missing")
    def test_xlsx_metadata_has_author(self):
        from doc2md import extract_doc_metadata
        path = FIXTURES / "sample.xlsx"
        meta = extract_doc_metadata(path, "xlsx")
        self.assertEqual(meta.get("author"), "Test Author")


# ---------------------------------------------------------------------------
# TestRstFixture — rst2md.py with real RST file
# ---------------------------------------------------------------------------

class TestRstFixture(unittest.TestCase):
    """rst2md.py with real fixture RST file (no model inference)."""

    @unittest.skipUnless(fixture_exists("sample.rst"), "sample.rst fixture missing")
    def test_rst_converts_without_error(self):
        from rst2md import rst_to_markdown_text
        rst = (FIXTURES / "sample.rst").read_text()
        result = rst_to_markdown_text(rst)
        self.assertIsInstance(result, str)
        self.assertGreater(len(result), 20)

    @unittest.skipUnless(fixture_exists("sample.rst"), "sample.rst fixture missing")
    def test_rst_conversion_contains_heading(self):
        from rst2md import rst_to_markdown_text
        rst = (FIXTURES / "sample.rst").read_text()
        result = rst_to_markdown_text(rst)
        self.assertIn("Test Document", result)

    @unittest.skipUnless(fixture_exists("sample.rst"), "sample.rst fixture missing")
    def test_rst_metadata_extracts_author(self):
        from rst2md import extract_rst_metadata
        path = FIXTURES / "sample.rst"
        rst = path.read_text()
        meta = extract_rst_metadata(rst, path)
        self.assertEqual(meta.get("author"), "Test Author")

    @unittest.skipUnless(fixture_exists("sample.rst"), "sample.rst fixture missing")
    def test_rst_metadata_extracts_title(self):
        from rst2md import extract_rst_metadata
        path = FIXTURES / "sample.rst"
        rst = path.read_text()
        meta = extract_rst_metadata(rst, path)
        self.assertEqual(meta.get("title"), "Test Document")

    @unittest.skipUnless(fixture_exists("sample.rst"), "sample.rst fixture missing")
    def test_rst_metadata_extracts_date(self):
        from rst2md import extract_rst_metadata
        path = FIXTURES / "sample.rst"
        rst = path.read_text()
        meta = extract_rst_metadata(rst, path)
        self.assertEqual(meta.get("date"), "2026-01-01")

    @unittest.skipUnless(fixture_exists("sample.rst"), "sample.rst fixture missing")
    def test_rst_metadata_extracts_version(self):
        from rst2md import extract_rst_metadata
        path = FIXTURES / "sample.rst"
        rst = path.read_text()
        meta = extract_rst_metadata(rst, path)
        self.assertEqual(meta.get("version"), "1.0")

    @unittest.skipUnless(fixture_exists("sample.rst"), "sample.rst fixture missing")
    def test_process_rst_file_creates_output(self):
        from rst2md import process_rst_file
        path = FIXTURES / "sample.rst"
        with tempfile.TemporaryDirectory() as tmpdir:
            out = process_rst_file(path, Path(tmpdir), "md")
            self.assertTrue(out.exists())
            content = out.read_text()
            self.assertIn("---", content)  # frontmatter present

    @unittest.skipUnless(fixture_exists("sample.rst"), "sample.rst fixture missing")
    def test_process_rst_file_frontmatter_has_author(self):
        from rst2md import process_rst_file
        path = FIXTURES / "sample.rst"
        with tempfile.TemporaryDirectory() as tmpdir:
            out = process_rst_file(path, Path(tmpdir), "md")
            content = out.read_text()
            self.assertIn("Test Author", content)


# ---------------------------------------------------------------------------
# TestHtmlFixture — html2md.py metadata extraction with real HTML file
# ---------------------------------------------------------------------------

class TestHtmlFixture(unittest.TestCase):
    """html2md.py metadata extraction with real HTML fixture (no model inference)."""

    @unittest.skipUnless(fixture_exists("sample.html"), "sample.html fixture missing")
    def test_html_reads_as_utf8(self):
        path = FIXTURES / "sample.html"
        content = path.read_text(encoding="utf-8")
        self.assertIn("<title>", content)

    @unittest.skipUnless(fixture_exists("sample.html"), "sample.html fixture missing")
    def test_html_meta_extraction_title(self):
        from html2md import extract_meta_tags
        html = (FIXTURES / "sample.html").read_text()
        meta = extract_meta_tags(html)
        self.assertEqual(meta.get("title"), "Test Page")

    @unittest.skipUnless(fixture_exists("sample.html"), "sample.html fixture missing")
    def test_html_meta_extraction_author(self):
        from html2md import extract_meta_tags
        html = (FIXTURES / "sample.html").read_text()
        meta = extract_meta_tags(html)
        self.assertEqual(meta.get("author"), "Test Author")

    @unittest.skipUnless(fixture_exists("sample.html"), "sample.html fixture missing")
    def test_html_description_extracted(self):
        from html2md import extract_meta_tags
        html = (FIXTURES / "sample.html").read_text()
        meta = extract_meta_tags(html)
        self.assertIn("description", meta)
        self.assertGreater(len(meta["description"]), 0)

    @unittest.skipUnless(fixture_exists("sample.html"), "sample.html fixture missing")
    def test_html_meta_all_three_keys(self):
        from html2md import extract_meta_tags
        html = (FIXTURES / "sample.html").read_text()
        meta = extract_meta_tags(html)
        self.assertIn("title", meta)
        self.assertIn("author", meta)
        self.assertIn("description", meta)


# ---------------------------------------------------------------------------
# TestPdfFixture — pdf2md.py with real born-digital PDF (no VLM)
# ---------------------------------------------------------------------------

class TestPdfFixture(unittest.TestCase):
    """pdf2md.py with real fixture PDF (text-layer, no VLM)."""

    @unittest.skipUnless(fixture_exists("sample.pdf"), "sample.pdf fixture missing")
    def test_pdf_extracts_pages(self):
        from pdf2md import extract_pages
        path = FIXTURES / "sample.pdf"
        pages = extract_pages(str(path))
        self.assertGreater(len(pages), 0)

    @unittest.skipUnless(fixture_exists("sample.pdf"), "sample.pdf fixture missing")
    def test_pdf_first_page_has_text(self):
        from pdf2md import extract_pages
        path = FIXTURES / "sample.pdf"
        pages = extract_pages(str(path))
        text = pages[0].get("text", "")
        self.assertGreater(len(text), 10)

    @unittest.skipUnless(fixture_exists("sample.pdf"), "sample.pdf fixture missing")
    def test_pdf_page_is_not_thin(self):
        from pdf2md import extract_pages, THIN_PAGE_THRESHOLD
        path = FIXTURES / "sample.pdf"
        pages = extract_pages(str(path))
        text = pages[0].get("text", "")
        self.assertGreater(len(text), THIN_PAGE_THRESHOLD)

    @unittest.skipUnless(fixture_exists("sample.pdf"), "sample.pdf fixture missing")
    def test_pdf_page_is_thin_flagged_false(self):
        from pdf2md import extract_pages
        path = FIXTURES / "sample.pdf"
        pages = extract_pages(str(path))
        # Born-digital PDF with ample text should NOT be flagged as thin
        self.assertFalse(pages[0]["is_thin"])

    @unittest.skipUnless(fixture_exists("sample.pdf"), "sample.pdf fixture missing")
    def test_pdf_metadata_extracted(self):
        import fitz
        from pdf2md import extract_pdf_metadata
        path = FIXTURES / "sample.pdf"
        doc = fitz.open(str(path))
        meta = extract_pdf_metadata(doc)
        doc.close()
        self.assertIn("pages", meta)
        self.assertEqual(meta["pages"], 1)

    @unittest.skipUnless(fixture_exists("sample.pdf"), "sample.pdf fixture missing")
    def test_pdf_metadata_has_fetched_at(self):
        import fitz
        from pdf2md import extract_pdf_metadata
        path = FIXTURES / "sample.pdf"
        doc = fitz.open(str(path))
        meta = extract_pdf_metadata(doc)
        doc.close()
        self.assertIn("fetched_at", meta)

    @unittest.skipUnless(fixture_exists("sample.pdf"), "sample.pdf fixture missing")
    def test_pdf_text_contains_expected_content(self):
        from pdf2md import extract_pages
        path = FIXTURES / "sample.pdf"
        pages = extract_pages(str(path))
        combined = " ".join(p["text"] for p in pages)
        self.assertIn("Test PDF Document", combined)


# ---------------------------------------------------------------------------
# TestImgFixture — img2md.py metadata extraction with real JPEG (no model)
# ---------------------------------------------------------------------------

class TestImgFixture(unittest.TestCase):
    """img2md.py metadata extraction with real fixture JPEG (no model inference)."""

    @unittest.skipUnless(fixture_exists("sample.jpg"), "sample.jpg fixture missing")
    def test_image_metadata_has_dimensions(self):
        from img2md import get_image_metadata
        path = FIXTURES / "sample.jpg"
        meta = get_image_metadata(path, "mlx-community/test-model")
        self.assertIn("width", meta)
        self.assertIn("height", meta)
        self.assertEqual(meta["width"], 200)
        self.assertEqual(meta["height"], 100)

    @unittest.skipUnless(fixture_exists("sample.jpg"), "sample.jpg fixture missing")
    def test_image_metadata_format(self):
        from img2md import get_image_metadata
        path = FIXTURES / "sample.jpg"
        meta = get_image_metadata(path, "test-model")
        self.assertEqual(meta.get("format"), "jpg")

    @unittest.skipUnless(fixture_exists("sample.jpg"), "sample.jpg fixture missing")
    def test_image_metadata_file_size(self):
        from img2md import get_image_metadata
        path = FIXTURES / "sample.jpg"
        meta = get_image_metadata(path, "test-model")
        self.assertGreater(meta.get("file_size_bytes", 0), 0)

    @unittest.skipUnless(fixture_exists("sample.jpg"), "sample.jpg fixture missing")
    def test_image_metadata_source_path(self):
        from img2md import get_image_metadata
        path = FIXTURES / "sample.jpg"
        meta = get_image_metadata(path, "test-model")
        self.assertIn("source", meta)
        self.assertIn("sample.jpg", meta["source"])

    @unittest.skipUnless(fixture_exists("sample.jpg"), "sample.jpg fixture missing")
    def test_image_metadata_has_model_used(self):
        from img2md import get_image_metadata
        path = FIXTURES / "sample.jpg"
        meta = get_image_metadata(path, "my-test-model")
        self.assertEqual(meta.get("model_used"), "my-test-model")

    @unittest.skipUnless(fixture_exists("sample.jpg"), "sample.jpg fixture missing")
    def test_image_metadata_has_fetched_at(self):
        from img2md import get_image_metadata
        path = FIXTURES / "sample.jpg"
        meta = get_image_metadata(path, "test-model")
        self.assertIn("fetched_at", meta)


# ---------------------------------------------------------------------------
# TestWeb2mdMetadata — web2md.py inline-HTML metadata (no network, no model)
# ---------------------------------------------------------------------------

class TestWeb2mdMetadata(unittest.TestCase):
    """web2md.py metadata extraction from inline HTML strings (no network)."""

    def test_extract_title_from_title_tag(self):
        from web2md import extract_metadata
        html = "<html><head><title>My Article</title></head><body></body></html>"
        meta = extract_metadata(html, "https://example.com/article")
        self.assertEqual(meta.get("title"), "My Article")

    def test_extract_description_from_og_meta(self):
        from web2md import extract_metadata
        html = (
            '<html><head>'
            '<meta name="description" content="Great article.">'
            '</head><body></body></html>'
        )
        meta = extract_metadata(html, "https://example.com/article")
        self.assertEqual(meta.get("description"), "Great article.")

    def test_url_preserved_in_metadata(self):
        from web2md import extract_metadata
        url = "https://example.com/page"
        meta = extract_metadata("<html><body></body></html>", url)
        self.assertEqual(meta.get("url"), url)

    def test_fetched_at_present(self):
        from web2md import extract_metadata
        meta = extract_metadata("<html></html>", "https://example.com")
        self.assertIn("fetched_at", meta)

    def test_sitename_derived_from_url(self):
        from web2md import extract_metadata
        meta = extract_metadata("<html></html>", "https://news.example.org/article")
        self.assertIn("sitename", meta)
        self.assertIn("example.org", meta["sitename"])


if __name__ == "__main__":
    unittest.main()
