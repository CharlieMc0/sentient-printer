"""Tests for filter pipeline and PDF tools."""

import io
import os
import tempfile
import unittest
from unittest.mock import patch, MagicMock

from fpdf import FPDF
from pypdf import PdfReader

from pdf_tools import create_commentary_page, append_commentary, extract_text


def _make_test_pdf(text: str = "Test document content") -> str:
    """Create a temp PDF with given text. Caller must delete the file."""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=12)
    pdf.cell(0, 10, text, new_x="LMARGIN", new_y="NEXT")
    tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
    tmp.write(pdf.output())
    tmp.close()
    return tmp.name


class TestCreateCommentaryPage(unittest.TestCase):
    def test_creates_valid_pdf(self):
        pdf_bytes = create_commentary_page("Corporate mediocrity at its finest.")
        self.assertIsInstance(pdf_bytes, (bytes, bytearray))
        self.assertTrue(pdf_bytes[:5] == b"%PDF-")

    def test_contains_header_text(self):
        pdf_bytes = create_commentary_page("Testing the commentary page.")
        reader = PdfReader(io.BytesIO(pdf_bytes))
        text = reader.pages[0].extract_text()
        self.assertIn("YOUR PRINTER HAS THOUGHTS", text)

    def test_handles_long_commentary(self):
        pdf_bytes = create_commentary_page("This is a very long commentary. " * 100)
        self.assertTrue(pdf_bytes[:5] == b"%PDF-")

    def test_handles_special_characters(self):
        pdf_bytes = create_commentary_page('Quotes "here" & apostrophe\'s <angles>')
        self.assertTrue(len(pdf_bytes) > 0)


class TestAppendCommentary(unittest.TestCase):
    def setUp(self):
        self.test_pdf = _make_test_pdf()

    def tearDown(self):
        os.unlink(self.test_pdf)

    def test_appends_page(self):
        output_path = self.test_pdf + ".out.pdf"
        try:
            append_commentary(self.test_pdf, "Great job printing this!", output_path)
            reader = PdfReader(output_path)
            self.assertEqual(len(reader.pages), 2)
        finally:
            if os.path.exists(output_path):
                os.unlink(output_path)

    def test_preserves_original(self):
        output_path = self.test_pdf + ".out.pdf"
        try:
            append_commentary(self.test_pdf, "Commentary here", output_path)
            reader = PdfReader(output_path)
            first_page_text = reader.pages[0].extract_text()
            self.assertIn("Test document", first_page_text)
        finally:
            if os.path.exists(output_path):
                os.unlink(output_path)


class TestExtractText(unittest.TestCase):
    def setUp(self):
        self.test_pdf = _make_test_pdf("Hello from the test PDF")

    def tearDown(self):
        os.unlink(self.test_pdf)

    def test_extracts_text(self):
        try:
            text = extract_text(self.test_pdf)
            self.assertIn("Hello from the test PDF", text)
        except FileNotFoundError:
            self.skipTest("pdftotext not installed (install poppler-utils)")


class TestFilterFailOpen(unittest.TestCase):
    """Test that the filter passes through on errors."""

    @patch("filter.enhance")
    def test_passthrough_on_enhance_failure(self, mock_enhance):
        from filter import passthrough

        tmp = _make_test_pdf("Original content")
        try:
            captured = io.BytesIO()
            with patch("sys.stdout", new_callable=lambda: MagicMock()):
                with patch("sys.stdout.buffer", captured):
                    passthrough(tmp)
            captured.seek(0)
            self.assertTrue(captured.read().startswith(b"%PDF-"))
        finally:
            os.unlink(tmp)


if __name__ == "__main__":
    unittest.main()
