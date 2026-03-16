"""Shared test fixtures for Sentient Printer."""

import os
import sys
import tempfile

import pytest

# Add src to path for all tests
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


@pytest.fixture
def sample_pdf(tmp_path):
    """Create a simple test PDF and return its path."""
    from fpdf import FPDF

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=12)
    pdf.cell(0, 10, "Test document content", new_x="LMARGIN", new_y="NEXT")
    path = tmp_path / "test.pdf"
    path.write_bytes(pdf.output())
    return str(path)
