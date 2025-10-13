import mimetypes
from typing import ClassVar
from wsgiref.util import FileWrapper

from django.db.models import Q, QuerySet
from django.http import Http404, HttpResponse
from drf_spectacular.utils import OpenApiExample, extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response

from core.context import Role
from core.permissions import (
    FileAccessPermission,
    FileListPermission,
    FileManagementPermission,
    PatientPermission,
    get_user_role,
)
from student_groups.models import ApprovedFile

from .models import File, Patient
from .serializers import FileSerializer, PatientSerializer
from .services import PdfPaginationService


class PatientViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing patient records.

    Provides CRUD operations for patients.
    - Students: read-only access
    - Instructors/Admins: full CRUD access
    """

    queryset = Patient.objects.all()
    serializer_class = PatientSerializer
    permission_classes: ClassVar[list[object]] = [PatientPermission]

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
                    "requires_pagination": True,
                },
                request_only=True,
            ),
            OpenApiExample(
                "Upload regular file",
                value={
                    "file": "document.txt",
                    "category": "Other",
                    "requires_pagination": False,
                },
                request_only=True,
            ),
        ],
    )
    @action(detail=True, methods=["post"], serializer_class=FileSerializer)
    def upload_file(self, request: Request, _pk: int | None = None) -> Response:
        """
        Upload a file for a specific patient.

        Note: This is a legacy endpoint. For new implementations,
        prefer using FileViewSet.create (POST /api/patients/{patient_pk}/files/).
        """
        patient = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(
            patient=patient,
            display_name=serializer.validated_data["file"].name,
        )
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def perform_create(self, serializer: object) -> None:
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
    - List action:
      - Students: Can view file lists (filtered to Admission files + approved files)
      - Instructors/Admins: Can view all files
    - Other CRUD actions:
      - Instructors/Admins: Full CRUD access (via FileManagementPermission)
      - Students: No direct CRUD access
    - File viewing (view action) uses separate FileAccessPermission

    File Categories:
    - Admission: Admission documents (always visible to students)
    - Pathology: Pathology reports
    - Imaging: Imaging results (X-rays, CT scans, etc.)
    - Diagnostics: Diagnostic test results
    - Lab Results: Laboratory test results
    - Other: Miscellaneous files
    """

    queryset = File.objects.all()
    serializer_class = FileSerializer
    permission_classes: ClassVar[list[object]] = [FileManagementPermission]

    def get_permissions(self) -> list[object]:
        """
        Use different permissions for list vs other actions.

        - List action: FileListPermission (allows students read-only access)
        - Other actions: FileManagementPermission (instructors/admins only)
        - View action: FileAccessPermission (defined in action decorator)
        """
        if self.action == "list":
            return [FileListPermission()]
        return super().get_permissions()

    def get_queryset(self) -> QuerySet:
        """
        Filter files by patient_pk from the nested route and user role.

        Filtering rules:
        - Students: Only see Admission files + approved files from completed requests
        - Instructors/Admins: See all files
        """
        base_queryset = File.objects.filter(patient_id=self.kwargs["patient_pk"])

        # For list action, filter based on user role
        if self.action == "list" and self.request.user.is_authenticated:
            user_role = get_user_role(self.request.user)

            # Students see only Admission files + approved files
            if user_role == Role.STUDENT.value:
                # Get files from approved lab requests for this student
                approved_file_ids = ApprovedFile.objects.filter(
                    Q(
                        imaging_request__user=self.request.user,
                        imaging_request__status="completed",
                    )
                    | Q(
                        blood_test_request__user=self.request.user,
                        blood_test_request__status="completed",
                    ),
                ).values_list("file_id", flat=True)

                # Filter: Admission category OR in approved files
                base_queryset = base_queryset.filter(
                    Q(category=File.Category.ADMISSION) | Q(id__in=approved_file_ids),
                ).distinct()

        return base_queryset

    @extend_schema(
        summary="List files for a patient",
        description=(
            "Returns files associated with a specific patient, filtered by user role:\n\n"
            "**Students:** Can view:\n"
            "- All Admission type files (always visible)\n"
            "- Files approved in their completed lab requests\n\n"
            "**Instructors/Admins:** Can view all files for the patient."
        ),
        responses={200: FileSerializer(many=True)},
    )
    def list(self, request: Request, *args: object, **kwargs: object) -> Response:
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
                    "requires_pagination": True,
                },
                request_only=True,
                description="Upload a PDF file with pagination enabled for granular access control",
            ),
            OpenApiExample(
                "Upload pathology report",
                value={
                    "file": "(binary data)",
                    "category": "Pathology",
                    "requires_pagination": False,
                },
                request_only=True,
                description="Upload a regular pathology report without pagination",
            ),
        ],
    )
    def create(self, request: Request, *args: object, **kwargs: object) -> Response:
        return super().create(request, *args, **kwargs)

    @extend_schema(
        summary="Retrieve file details",
        description="Get metadata for a specific file including category, pagination status, and creation date. "
        "Only accessible by instructors and admins.",
        responses={200: FileSerializer},
    )
    def retrieve(self, request: Request, *args: object, **kwargs: object) -> Response:
        return super().retrieve(request, *args, **kwargs)

    @extend_schema(
        summary="Update file metadata",
        description="Update file metadata such as category or pagination settings. "
        "Note: The actual file content cannot be updated - delete and recreate instead. "
        "Only accessible by instructors and admins.",
        request=FileSerializer,
        responses={200: FileSerializer},
    )
    def update(self, request: Request, *args: object, **kwargs: object) -> Response:
        return super().update(request, *args, **kwargs)

    @extend_schema(
        summary="Partially update file metadata",
        description="Partially update file metadata such as category or pagination settings. "
        "Only accessible by instructors and admins.",
        request=FileSerializer,
        responses={200: FileSerializer},
    )
    def partial_update(
        self, request: Request, *args: object, **kwargs: object
    ) -> Response:
        return super().partial_update(request, *args, **kwargs)

    @extend_schema(
        summary="Delete a file",
        description="Delete a file and remove it from disk. "
        "This will also remove any approved file associations. "
        "Only accessible by instructors and admins.",
        responses={204: None},
    )
    def destroy(self, request: Request, *args: object, **kwargs: object) -> Response:
        return super().destroy(request, *args, **kwargs)

    def perform_create(self, serializer: object) -> None:
        """
        Override perform_create to automatically set the patient from the URL.
        The patient_pk comes from the nested route.
        """
        patient_id = self.kwargs.get("patient_pk")
        serializer.save(patient_id=patient_id)

    @extend_schema(
        summary="View a specific file",
        description=(
            "View file content with role-based access control.\n\n"
            "**For non-paginated files:** Returns the entire file.\n\n"
            "**For paginated PDFs (requires_pagination=True):**\n"
            "- **Instructors/Admins:**\n"
            "  - Without `?page_range` parameter: Returns the entire PDF file\n"
            "  - With `?page_range` parameter: Returns specified pages\n"
            "    - `?page_range=5` - View a single page\n"
            "    - `?page_range=1-5` - View a range of pages\n"
            "    - `?page_range=1-5,7,10-12` - View multiple pages/ranges\n"
            "- **Students:** Can only view pages from approved lab requests (ApprovedFile.page_range).\n"
            "  Students can optionally specify pages within their approved range.\n\n"
            "**Authorization:**\n"
            "- Students: Must have a completed lab request with an ApprovedFile for this file\n"
            "- Instructors/Admins: Full access to all files and pages\n\n"
            "**Error Handling:**\n"
            "- Invalid page ranges will return an error with the valid page range"
        ),
    )
    @action(detail=True, methods=["get"], permission_classes=[FileAccessPermission])
    def view(
        self, request: Request, _pk: int | None = None, _patient_pk: int | None = None
    ) -> HttpResponse | Response:
        """
        View file content with pagination support for PDFs.

        Role-based access control:
        - Instructors/Admins: Full access to all files and optional page ranges
        - Students: Restricted to approved page ranges from completed lab requests
        """
        file_instance = self.get_object()
        page_range_query = request.query_params.get("page_range")

        # For paginated PDFs, check if we need pagination or full file
        if file_instance.requires_pagination:
            user_role = get_user_role(request.user)

            # Instructors/admins without page_range get the full file
            if (
                user_role in [Role.ADMIN.value, Role.INSTRUCTOR.value]
                and not page_range_query
            ):
                return self._serve_whole_file(file_instance)

            # Use pagination service for page extraction
            pdf_service = PdfPaginationService()
            return pdf_service.serve_paginated_pdf(
                file_instance,
                request.user,
                page_range_query,
            )

        # For non-paginated files, serve the whole file
        return self._serve_whole_file(file_instance)

    def _serve_whole_file(self, file_instance: object) -> HttpResponse:
        """Serve the entire file content"""
        try:
            wrapper = FileWrapper(file_instance.file.open("rb"))
            content_type = mimetypes.guess_type(file_instance.file.name)[0]
            response = HttpResponse(wrapper, content_type=content_type)
        except FileNotFoundError as exc:
            msg = "File not found"
            raise Http404(msg) from exc
        else:
            response["Content-Disposition"] = (
                f"inline; filename={file_instance.display_name}"
            )
            return response
