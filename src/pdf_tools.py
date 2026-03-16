"""PDF text extraction and modification for Sentient Printer."""

import io

from fpdf import FPDF
from pypdf import PdfReader, PdfWriter


def extract_text(pdf_path: str) -> str:
    """Extract text from a PDF using pypdf.

    Args:
        pdf_path: Path to the PDF file.

    Returns:
        Extracted text string.
    """
    reader = PdfReader(pdf_path)
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def create_commentary_page(commentary: str) -> bytes:
    """Generate a single PDF page with commentary text.

    Args:
        commentary: The LLM-generated commentary string.

    Returns:
        PDF bytes for the commentary page.
    """
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=25)

    # Header
    pdf.set_font("Helvetica", "B", 20)
    pdf.cell(0, 15, "YOUR PRINTER HAS THOUGHTS", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.ln(5)

    # Divider line
    pdf.set_draw_color(100, 100, 100)
    pdf.set_line_width(0.5)
    pdf.line(20, pdf.get_y(), 190, pdf.get_y())
    pdf.ln(10)

    # Commentary text
    pdf.set_font("Helvetica", "", 14)
    pdf.multi_cell(0, 8, commentary)
    pdf.ln(10)

    # Footer
    pdf.set_font("Helvetica", "I", 9)
    pdf.set_text_color(130, 130, 130)
    pdf.cell(0, 10, "Printed with opinions by Sentient Printer", new_x="LMARGIN", new_y="NEXT", align="C")

    return pdf.output()


def append_commentary(original_pdf_path: str, commentary: str, output_path: str) -> None:
    """Append a commentary page to the original PDF.

    Args:
        original_pdf_path: Path to the original PDF.
        commentary: The LLM-generated commentary string.
        output_path: Where to write the combined PDF.
    """
    commentary_bytes = create_commentary_page(commentary)

    writer = PdfWriter()

    # Add all original pages
    reader = PdfReader(original_pdf_path)
    for page in reader.pages:
        writer.add_page(page)

    # Add commentary page
    commentary_reader = PdfReader(io.BytesIO(commentary_bytes))
    for page in commentary_reader.pages:
        writer.add_page(page)

    with open(output_path, "wb") as f:
        writer.write(f)
