"""
PDF pagination service module.

This module provides services for handling PDF pagination with role-based
access control. It separates PDF processing logic from view layer concerns,
making the code more testable and maintainable.
"""

import io

from django.http import HttpResponse
from PyPDF2 import PdfReader, PdfWriter
from rest_framework import status
from rest_framework.response import Response

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
    def parse(range_str: str | None) -> list[int]:
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
        for segment in range_str.split(","):
            part = segment.strip()
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
    def get_authorized_page_range(file_instance: object, user: object) -> str | None:
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

    def __init__(self) -> None:
        """Initialize the PDF pagination service."""
        self.auth_service = PdfAuthorizationService()
        self.parser = PdfPageRangeParser()

    def serve_paginated_pdf(
        self,
        file_instance: object,
        user: object,
        page_range_query: str,
    ) -> Response:
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
            Response with PDF content or Response with error message

        Authorization rules:
            - Instructors/Admins: Can access any page range
            - Students: Restricted to ApprovedFile page_range from completed requests
        """
        try:
            user_role = get_user_role(user)
            authorized_range = self.auth_service.get_authorized_page_range(
                file_instance,
                user,
            )

            # Check if student has any access to this file
            if authorized_range is None and user_role == Role.STUDENT.value:
                return Response(
                    {"detail": "No authorized page range found for this file."},
                    status=status.HTTP_403_FORBIDDEN,
                )

            # Parse requested pages
            if page_range_query:
                requested_pages = self.parser.parse(page_range_query)
            elif authorized_range:
                # Students without explicit query get their approved range
                requested_pages = self.parser.parse(authorized_range)
            else:
                return Response(
                    {"detail": "No page range specified."},
                    status=status.HTTP_403_FORBIDDEN,
                )

            # Validate and extract pages
            return self._process_pdf_pages(
                file_instance,
                requested_pages,
                authorized_range,
                user_role,
            )

        except Exception as exc:  # noqa: BLE001 - fallback to forbid on unexpected PDF processing errors
            return Response(
                {"detail": f"Error processing PDF: {exc!s}"},
                status=status.HTTP_403_FORBIDDEN,
            )

    def _process_pdf_pages(
        self,
        file_instance: object,
        requested_pages: list[int],
        authorized_range: str | None,
        user_role: str,
    ) -> Response:
        """
        Process and extract requested pages from PDF.

        Args:
            file_instance: The File object containing the PDF
            requested_pages: List of page numbers to extract
            authorized_range: Authorized page range string for students
            user_role: Role of the requesting user

        Returns:
            Response with extracted PDF pages or Response with error message
        """
        with file_instance.file.open("rb") as pdf_file:
            reader = PdfReader(pdf_file)
            total_pages = len(reader.pages)

            # Validate that all requested pages exist in the PDF
            validation_error = self._validate_pages(
                requested_pages,
                total_pages,
                authorized_range,
                user_role,
            )
            if validation_error:
                return validation_error

            # Extract the requested pages
            return self._extract_and_respond(
                reader,
                requested_pages,
                file_instance.display_name,
            )

    def _validate_pages(
        self,
        requested_pages: list[int],
        total_pages: int,
        authorized_range: str | None,
        user_role: str,
    ) -> Response | None:
        """
        Validate that requested pages exist and are authorized.

        Args:
            requested_pages: List of page numbers to validate
            total_pages: Total number of pages in the PDF
            authorized_range: Authorized page range for students
            user_role: Role of the requesting user

        Returns:
            Response with error message if validation fails, None if valid
        """
        # Check if pages exist in PDF
        invalid_pages = [
            page for page in requested_pages if page < 1 or page > total_pages
        ]
        if invalid_pages:
            return Response(
                {
                    "detail": (
                        "Invalid page range. Valid pages: 1-{total_pages}. "
                        "Invalid pages requested: {invalid}".format(
                            total_pages=total_pages,
                            invalid=", ".join(map(str, invalid_pages)),
                        )
                    )
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        # For students, verify requested pages are within authorized range
        if user_role == Role.STUDENT.value and authorized_range:
            authorized_pages = self.parser.parse(authorized_range)
            unauthorized_pages = [
                page for page in requested_pages if page not in authorized_pages
            ]
            if unauthorized_pages:
                return Response(
                    {
                        "detail": (
                            "Requested pages are not authorized. Your approved range is: {auth}. "
                            "Unauthorized pages: {unauth}".format(
                                auth=authorized_range,
                                unauth=", ".join(map(str, unauthorized_pages)),
                            )
                        )
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )

        return None

    def _extract_and_respond(
        self,
        reader: PdfReader,
        requested_pages: list[int],
        display_name: str,
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
            output_buffer.getvalue(),
            content_type="application/pdf",
        )
        filename = f"{display_name}_pages_{'-'.join(map(str, requested_pages))}.pdf"
        response["Content-Disposition"] = f'inline; filename="{filename}"'
        return response
