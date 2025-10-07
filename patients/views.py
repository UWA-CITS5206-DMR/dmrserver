import mimetypes
import io
from wsgiref.util import FileWrapper
from django.http import Http404, HttpResponse, HttpResponseForbidden
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiExample
from PyPDF2 import PdfReader, PdfWriter

from core.permissions import (
    PatientPermission,
    FileAccessPermission,
    FileManagementPermission,
)
from .models import Patient, File
from .serializers import PatientSerializer, FileSerializer


class PatientViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing patient records.
    
    Provides CRUD operations for patients.
    - Students: read-only access
    - Instructors/Admins: full CRUD access
    """
    queryset = Patient.objects.all()
    serializer_class = PatientSerializer
    permission_classes = [PatientPermission]

    @extend_schema(
        summary="Upload file for patient (Legacy)",
        description="Legacy endpoint for uploading files to a patient. "
                    "Consider using POST /api/patients/{patient_pk}/files/ instead for better REST compliance. "
                    "This endpoint supports file upload with category and pagination settings.",
        request=FileSerializer,
        responses={201: FileSerializer},
        examples=[
            OpenApiExample(
                "Upload PDF with pagination",
                value={
                    "file": "file.pdf",
                    "category": "Imaging",
                    "requires_pagination": True
                },
                request_only=True,
            ),
            OpenApiExample(
                "Upload regular file",
                value={
                    "file": "document.txt",
                    "category": "Other",
                    "requires_pagination": False
                },
                request_only=True,
            ),
        ],
    )
    @action(detail=True, methods=["post"], serializer_class=FileSerializer)
    def upload_file(self, request, pk=None):
        """
        Upload a file for a specific patient.
        
        Note: This is a legacy endpoint. For new implementations,
        prefer using FileViewSet.create (POST /api/patients/{patient_pk}/files/).
        """
        patient = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(
            patient=patient, display_name=serializer.validated_data["file"].name
        )
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def perform_create(self, serializer):
        serializer.save()


class FileViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing patient files.
    
    Provides full CRUD operations for file management:
    - List files for a specific patient
    - Create/upload new files with category and pagination settings
    - Retrieve file details
    - Update file metadata (category, pagination settings)
    - Delete files (removes from disk)
    - View file content with optional PDF pagination
    
    Permissions:
    - Instructors/Admins: Full CRUD access (via FileManagementPermission)
    - Students: No direct CRUD access
    - File viewing (view action) uses separate FileAccessPermission
    
    File Categories:
    - Admission: Admission documents
    - Pathology: Pathology reports
    - Imaging: Imaging results (X-rays, CT scans, etc.)
    - Diagnostics: Diagnostic test results
    - Lab Results: Laboratory test results
    - Other: Miscellaneous files
    """
    queryset = File.objects.all()
    serializer_class = FileSerializer
    permission_classes = [FileManagementPermission]

    def get_queryset(self):
        """Filter files by patient_pk from the nested route."""
        return File.objects.filter(patient_id=self.kwargs["patient_pk"])

    @extend_schema(
        summary="List files for a patient",
        description="Returns all files associated with a specific patient. "
                    "Only accessible by instructors and admins.",
        responses={200: FileSerializer(many=True)},
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(
        summary="Upload a new file",
        description="Upload a new file for a patient. "
                    "The file can be categorized using the 'category' field. "
                    "For PDF files, set 'requires_pagination' to true to enable page-based authorization. "
                    "Only accessible by instructors and admins.",
        request=FileSerializer,
        responses={201: FileSerializer},
        examples=[
            OpenApiExample(
                "Upload PDF with pagination enabled",
                value={
                    "file": "(binary data)",
                    "category": "Imaging",
                    "requires_pagination": True
                },
                request_only=True,
                description="Upload a PDF file with pagination enabled for granular access control"
            ),
            OpenApiExample(
                "Upload pathology report",
                value={
                    "file": "(binary data)",
                    "category": "Pathology",
                    "requires_pagination": False
                },
                request_only=True,
                description="Upload a regular pathology report without pagination"
            ),
        ],
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @extend_schema(
        summary="Retrieve file details",
        description="Get metadata for a specific file including category, pagination status, and creation date. "
                    "Only accessible by instructors and admins.",
        responses={200: FileSerializer},
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @extend_schema(
        summary="Update file metadata",
        description="Update file metadata such as category or pagination settings. "
                    "Note: The actual file content cannot be updated - delete and recreate instead. "
                    "Only accessible by instructors and admins.",
        request=FileSerializer,
        responses={200: FileSerializer},
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @extend_schema(
        summary="Partially update file metadata",
        description="Partially update file metadata such as category or pagination settings. "
                    "Only accessible by instructors and admins.",
        request=FileSerializer,
        responses={200: FileSerializer},
    )
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @extend_schema(
        summary="Delete a file",
        description="Delete a file and remove it from disk. "
                    "This will also remove any approved file associations. "
                    "Only accessible by instructors and admins.",
        responses={204: None},
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)

    def perform_create(self, serializer):
        """
        Override perform_create to automatically set the patient from the URL.
        The patient_pk comes from the nested route.
        """
        patient_id = self.kwargs.get('patient_pk')
        serializer.save(patient_id=patient_id)

    @extend_schema(
        summary="View a specific file",
        description="Allows users with permission to view a file's content. For paginated PDFs, a 'page' or 'range' query parameter can be used.",
    )
    @action(detail=True, methods=["get"], permission_classes=[FileAccessPermission])
    def view(self, request, pk=None, patient_pk=None):
        file_instance = self.get_object()

        if not request.user.is_authenticated:
            return HttpResponseForbidden("Authentication required.")

        page_query = request.query_params.get("page")
        range_query = request.query_params.get("range")

        if file_instance.requires_pagination:
            return self._serve_paginated_pdf(
                file_instance, request.user, page_query, range_query
            )

        # For non-paginated files, serve the whole file
        return self._serve_whole_file(file_instance)

    def _get_authorized_page_range(self, file_instance, user):
        """Get the authorized page range for a user from approved imaging requests"""
        from student_groups.models import ApprovedFile

        if user.is_staff:
            return None  # Staff can access all pages

        approved_file = ApprovedFile.objects.filter(
            file=file_instance,
            imaging_request__user=user,
            imaging_request__status="completed",
        ).first()

        return approved_file.page_range if approved_file else None

    def _parse_page_range(self, range_str):
        """Parse page range string like '1-5' or '7' into a list of page numbers"""
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

    def _serve_paginated_pdf(self, file_instance, user, page_query, range_query):
        """Serve specific pages of a PDF file based on authorization"""
        try:
            authorized_range = self._get_authorized_page_range(file_instance, user)

            if not authorized_range and not user.is_staff:
                return HttpResponseForbidden(
                    "No authorized page range found for this file."
                )

            # Determine which pages to extract
            if page_query:
                requested_pages = [int(page_query)]
            elif range_query:
                requested_pages = self._parse_page_range(range_query)
            elif authorized_range:
                requested_pages = self._parse_page_range(authorized_range)
            else:
                return HttpResponseForbidden("No page range specified.")

            # For non-staff users, verify requested pages are within authorized range
            if not user.is_staff and authorized_range:
                authorized_pages = self._parse_page_range(authorized_range)
                if not all(page in authorized_pages for page in requested_pages):
                    return HttpResponseForbidden("Requested pages are not authorized.")

            # Extract pages from PDF
            with file_instance.file.open("rb") as pdf_file:
                reader = PdfReader(pdf_file)
                writer = PdfWriter()

                total_pages = len(reader.pages)

                for page_num in requested_pages:
                    if 1 <= page_num <= total_pages:
                        writer.add_page(
                            reader.pages[page_num - 1]
                        )  # Convert to 0-based index

                if len(writer.pages) == 0:
                    return HttpResponseForbidden(
                        "No valid pages found in the requested range."
                    )

                # Create response with extracted pages
                output_buffer = io.BytesIO()
                writer.write(output_buffer)
                output_buffer.seek(0)

                response = HttpResponse(
                    output_buffer.getvalue(), content_type="application/pdf"
                )
                filename = f"{file_instance.display_name}_pages_{'-'.join(map(str, requested_pages))}.pdf"
                response["Content-Disposition"] = f'inline; filename="{filename}"'
                return response

        except Exception as e:
            return HttpResponseForbidden(f"Error processing PDF: {str(e)}")

    def _serve_whole_file(self, file_instance):
        """Serve the entire file content"""
        try:
            wrapper = FileWrapper(file_instance.file.open("rb"))
            content_type = mimetypes.guess_type(file_instance.file.name)[0]
            response = HttpResponse(wrapper, content_type=content_type)
            response["Content-Disposition"] = (
                f"inline; filename={file_instance.display_name}"
            )
            return response
        except FileNotFoundError:
            raise Http404("File not found")
