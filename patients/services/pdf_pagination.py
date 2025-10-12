"""
PDF pagination service module.

This module provides services for handling PDF pagination with role-based
access control. It separates PDF processing logic from view layer concerns,
making the code more testable and maintainable.
"""

import io
from typing import Optional, List
from django.http import HttpResponse, HttpResponseForbidden
from PyPDF2 import PdfReader, PdfWriter

from core.context import Role
from core.permissions import get_user_role
from student_groups.models import ApprovedFile


class PdfPageRangeParser:
    """
    Utility class for parsing page range strings.

    Supports various formats:
    - Single page: "5" -> [5]
    - Range: "1-5" -> [1, 2, 3, 4, 5]
    - Multiple ranges: "1-3,5,7-9" -> [1, 2, 3, 5, 7, 8, 9]
    """

    @staticmethod
    def parse(range_str: Optional[str]) -> List[int]:
        """
        Parse page range string into a list of page numbers.

        Args:
            range_str: Page range string (e.g., "1-5,7,10-12") or None

        Returns:
            List of page numbers (empty list if range_str is None)

        Examples:
            >>> PdfPageRangeParser.parse("5")
            [5]
            >>> PdfPageRangeParser.parse("1-3")
            [1, 2, 3]
            >>> PdfPageRangeParser.parse("1-3,5,7-9")
            [1, 2, 3, 5, 7, 8, 9]
        """
        if not range_str:
            return []

        pages = []
        for part in range_str.split(","):
            part = part.strip()
            if "-" in part:
                start, end = map(int, part.split("-"))
                pages.extend(range(start, end + 1))
            else:
                pages.append(int(part))
        return pages


class PdfAuthorizationService:
    """
    Service for determining authorized PDF page ranges for users.

    Implements role-based authorization:
    - Admin/Instructor: Unrestricted access to all pages (returns None)
    - Student: Access restricted to approved page ranges from completed lab requests
    """

    @staticmethod
    def get_authorized_page_range(file_instance, user) -> Optional[str]:
        """
        Get the authorized page range for a user accessing a file.

        Args:
            file_instance: The File object being accessed
            user: The requesting user (Django User object)

        Returns:
            - None for instructors/admins (unrestricted access)
            - page_range string for students with approved access (e.g., "1-5,7")
            - None for students without approved access (access will be denied)

        Business rules:
            - Admins and instructors have unrestricted access to all pages
            - Students must have an ApprovedFile from a completed lab request
            - Lab requests can be ImagingRequest or BloodTestRequest
        """
        user_role = get_user_role(user)

        # Instructors and admins have unrestricted access to all pages
        if user_role in [Role.ADMIN.value, Role.INSTRUCTOR.value]:
            return None

        # Students must have an approved lab request for this file
        # Check ImagingRequest first
        approved_file = ApprovedFile.objects.filter(
            file=file_instance,
            imaging_request__user=user,
            imaging_request__status="completed",
        ).first()

        if not approved_file:
            # If not found in ImagingRequest, check BloodTestRequest
            approved_file = ApprovedFile.objects.filter(
                file=file_instance,
                blood_test_request__user=user,
                blood_test_request__status="completed",
            ).first()

        return approved_file.page_range if approved_file else None


class PdfPaginationService:
    """
    Service for handling PDF page extraction with authorization.

    This service extracts specific pages from PDF files based on user authorization.
    The view layer should handle role checks and determine when to call this service.
    """

    def __init__(self):
        """Initialize the PDF pagination service."""
        self.auth_service = PdfAuthorizationService()
        self.parser = PdfPageRangeParser()

    def serve_paginated_pdf(
        self, file_instance, user, page_range_query: str
    ) -> HttpResponse:
        """
        Serve specific pages of a PDF file based on user authorization.

        Args:
            file_instance: The File object to serve
            user: The requesting user
            page_range_query: Page range string from query params (required)
                Examples: "5" (single page)
                         "1-5" (range)
                         "1-5,7,10-12" (multiple ranges)

        Returns:
            HttpResponse with PDF content or HttpResponseForbidden

        Authorization rules:
            - Instructors/Admins: Can access any page range
            - Students: Restricted to ApprovedFile page_range from completed requests
        """
        try:
            user_role = get_user_role(user)
            authorized_range = self.auth_service.get_authorized_page_range(
                file_instance, user
            )

            # Check if student has any access to this file
            if authorized_range is None and user_role == Role.STUDENT.value:
                return HttpResponseForbidden(
                    "No authorized page range found for this file."
                )

            # Parse requested pages
            if page_range_query:
                requested_pages = self.parser.parse(page_range_query)
            elif authorized_range:
                # Students without explicit query get their approved range
                requested_pages = self.parser.parse(authorized_range)
            else:
                return HttpResponseForbidden("No page range specified.")

            # Validate and extract pages
            return self._process_pdf_pages(
                file_instance, requested_pages, authorized_range, user_role
            )

        except Exception as e:
            return HttpResponseForbidden(f"Error processing PDF: {str(e)}")

    def _process_pdf_pages(
        self,
        file_instance,
        requested_pages: List[int],
        authorized_range: Optional[str],
        user_role: str,
    ) -> HttpResponse:
        """
        Process and extract requested pages from PDF.

        Args:
            file_instance: The File object containing the PDF
            requested_pages: List of page numbers to extract
            authorized_range: Authorized page range string for students
            user_role: Role of the requesting user

        Returns:
            HttpResponse with extracted PDF pages or HttpResponseForbidden
        """
        with file_instance.file.open("rb") as pdf_file:
            reader = PdfReader(pdf_file)
            total_pages = len(reader.pages)

            # Validate that all requested pages exist in the PDF
            validation_error = self._validate_pages(
                requested_pages, total_pages, authorized_range, user_role
            )
            if validation_error:
                return validation_error

            # Extract the requested pages
            return self._extract_and_respond(
                reader, requested_pages, file_instance.display_name
            )

    def _validate_pages(
        self,
        requested_pages: List[int],
        total_pages: int,
        authorized_range: Optional[str],
        user_role: str,
    ) -> Optional[HttpResponseForbidden]:
        """
        Validate that requested pages exist and are authorized.

        Args:
            requested_pages: List of page numbers to validate
            total_pages: Total number of pages in the PDF
            authorized_range: Authorized page range for students
            user_role: Role of the requesting user

        Returns:
            HttpResponseForbidden if validation fails, None if valid
        """
        # Check if pages exist in PDF
        invalid_pages = [
            page for page in requested_pages if page < 1 or page > total_pages
        ]
        if invalid_pages:
            return HttpResponseForbidden(
                "Invalid page range. Valid pages: 1-{}. Invalid pages requested: {}".format(
                    total_pages, ", ".join(map(str, invalid_pages))
                )
            )

        # For students, verify requested pages are within authorized range
        if user_role == Role.STUDENT.value and authorized_range:
            authorized_pages = self.parser.parse(authorized_range)
            unauthorized_pages = [
                page for page in requested_pages if page not in authorized_pages
            ]
            if unauthorized_pages:
                return HttpResponseForbidden(
                    "Requested pages are not authorized. Your approved range is: {}. Unauthorized pages: {}".format(
                        authorized_range, ", ".join(map(str, unauthorized_pages))
                    )
                )

        return None

    def _extract_and_respond(
        self, reader: PdfReader, requested_pages: List[int], display_name: str
    ) -> HttpResponse:
        """
        Extract pages from PDF and create HTTP response.

        Args:
            reader: PdfReader object with the source PDF
            requested_pages: List of page numbers to extract
            display_name: Original filename for response headers

        Returns:
            HttpResponse with extracted PDF content
        """
        writer = PdfWriter()
        for page_num in requested_pages:
            writer.add_page(reader.pages[page_num - 1])  # Convert to 0-based index

        # Create response with extracted pages
        output_buffer = io.BytesIO()
        writer.write(output_buffer)
        output_buffer.seek(0)

        response = HttpResponse(
            output_buffer.getvalue(), content_type="application/pdf"
        )
        filename = f"{display_name}_pages_{'-'.join(map(str, requested_pages))}.pdf"
        response["Content-Disposition"] = f'inline; filename="{filename}"'
        return response
