"""
Patient services package.

This package contains service classes that encapsulate business logic
for patient-related operations, keeping views clean and focused on HTTP concerns.
"""

from .pdf_pagination import PdfPaginationService

__all__ = ["PdfPaginationService"]
