"""
Test utilities for the DMR project.

This module provides common utility functions used across test files.
"""

from io import BytesIO

from PyPDF2 import PdfWriter


def create_test_pdf(num_pages=1, width=612, height=792):
    """
    Create a valid test PDF with proper structure.

    This function generates a properly formatted PDF file using PyPDF2 to avoid
    "incorrect startxref pointer" warnings during tests. The generated PDF has
    a correct xref table and trailer structure.

    Args:
        num_pages: Number of blank pages to include in the PDF (default: 1)
        width: Page width in points (default: 612 - letter size)
        height: Page height in points (default: 792 - letter size)

    Returns:
        bytes: PDF file content as bytes

    Example:
        >>> pdf_content = create_test_pdf(num_pages=5)
        >>> # Use pdf_content in test file uploads
    """
    writer = PdfWriter()

    for _ in range(num_pages):
        writer.add_blank_page(width=width, height=height)

    buffer = BytesIO()
    writer.write(buffer)
    buffer.seek(0)

    return buffer.read()
