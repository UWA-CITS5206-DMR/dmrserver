import mimetypes
from typing import ClassVar
from wsgiref.util import FileWrapper

from django.db.models import Q, QuerySet
from django.http import Http404
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response

from core.cache import CacheMixin
from core.context import Role
from core.permissions import (
    FileAccessPermission,
    GoogleFormLinkPermission,
    PatientPermission,
    get_user_role,
)
from student_groups.models import ApprovedFile

from .models import File, GoogleFormLink, Patient
from .serializers import (
    FileSerializer,
    GoogleFormLinkSerializer,
    ManualFileReleaseResponseSerializer,
    ManualFileReleaseSerializer,
    PatientSerializer,
)
from .services import PdfPaginationService


class PatientViewSet(CacheMixin, viewsets.ModelViewSet):
    """
    ViewSet for managing patient records.

    Provides CRUD operations for patients with caching:
    - Students: read-only access
    - Instructors/Admins: full CRUD access
    - Automatic response caching on list and retrieve actions
    - Automatic cache invalidation on create/update/destroy actions
    """

    queryset = Patient.objects.all()
    serializer_class = PatientSerializer
    permission_classes: ClassVar[list[object]] = [PatientPermission]
    cache_app: str = "patients"
    cache_model: str = "patients"
    cache_key_params: ClassVar[list[str]] = []
    cache_invalidate_params: ClassVar[list[str]] = ["id"]
    cache_user_sensitive: ClassVar[bool] = False


class FileViewSet(CacheMixin, viewsets.ModelViewSet):
    """
    ViewSet for managing patient files.

    Provides full CRUD operations for file management:
    - List files for a specific patient
    - Create/upload new files with category and pagination settings
    - Retrieve file details
    - Update file metadata (category, pagination settings)
    - Delete files (removes from disk)
    - View file content with optional PDF pagination

    Uses CacheMixin for automatic caching and invalidation.
    Cache invalidation is triggered on create/update/delete.
    """

    queryset = File.objects.all()
    serializer_class = FileSerializer
    permission_classes: ClassVar[list[object]] = [FileAccessPermission]
    cache_app: str = "patients"
    cache_model: str = "files"
    cache_key_params: ClassVar[list[str]] = ["patient_pk"]
    cache_invalidate_params: ClassVar[list[str]] = ["patient_id"]
    cache_user_sensitive: ClassVar[bool] = True

    def get_queryset(self) -> QuerySet:
        """
        Filter files by patient_pk from the nested route and user role.

        Filtering rules:
        - Students: Only see Admission files + approved files from completed investigation requests or manual releases
        - Instructors/Admins: See all files
        """
        base_queryset = File.objects.filter(patient_id=self.kwargs["patient_pk"])

        # For list action, filter based on user role
        if self.action == "list":
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
                    )
                    | Q(released_to_user=self.request.user)
                ).values_list("file_id", flat=True)

                # Filter: Admission category OR in approved files
                base_queryset = base_queryset.filter(
                    Q(category=File.Category.ADMISSION) | Q(id__in=approved_file_ids),
                ).distinct()

        return base_queryset

    @extend_schema(
        summary="Manually release file access to student groups",
        description=(
            "Grant one or more student group accounts access to this file without requiring "
            "an investigation request. For paginated PDF files, a page range must be supplied."
        ),
        request=ManualFileReleaseSerializer,
        responses={
            200: OpenApiResponse(response=ManualFileReleaseResponseSerializer),
        },
    )
    @action(detail=True, methods=["post"])
    def release(
        self,
        request: Request,
        *_args: object,
        **_kwargs: object,
    ) -> Response:
        file_instance = self.get_object()
        serializer = ManualFileReleaseSerializer(
            data=request.data,
            context={"file": file_instance},
        )
        serializer.is_valid(raise_exception=True)

        approved_files = serializer.save(released_by=request.user)
        released_users = [
            obj.released_to_user for obj in approved_files if obj.released_to_user
        ]

        response_payload = {
            "file_id": str(file_instance.id),
            "released_to": released_users,
            "page_range": serializer.validated_data.get("page_range", ""),
        }
        response_serializer = ManualFileReleaseResponseSerializer(response_payload)
        return Response(response_serializer.data, status=status.HTTP_200_OK)

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
            "- **Students:** Can only view pages within their approved range from completed investigation requests or manual releases.\n"
            "  Students can optionally specify pages within their approved range.\n\n"
            "**Authorization:**\n"
            "- Students: Must have a completed investigation request with an ApprovedFile for this file, or the file must be manually released to their student group\n"
            "- Instructors/Admins: Full access to all files and pages\n\n"
            "**Error Handling:**\n"
            "- Invalid page ranges will return an error with the valid page range"
        ),
    )
    @action(detail=True, methods=["get"])
    def view(self, request: Request, *_args: object, **_kwargs: object) -> Response:
        """
        View file content with pagination support for PDFs.

        Role-based access control:
        - Instructors/Admins: Full access to all files and optional page ranges
        - Students: Restricted to approved page ranges from completed investigation requests or manual releases
        """
        file_instance = self.get_object()
        page_range_query = request.query_params.get("page_range")

        def serve_whole_file(file_instance: object) -> Response:
            """Serve the entire file content"""
            try:
                wrapper = FileWrapper(file_instance.file.open("rb"))
                content_type = mimetypes.guess_type(file_instance.file.name)[0]
                response = Response()
                response.content = wrapper
                response["Content-Type"] = content_type
            except FileNotFoundError as exc:
                msg = "File not found"
                raise Http404(msg) from exc
            else:
                response["Content-Disposition"] = (
                    f"inline; filename={file_instance.display_name}"
                )
                return response

        # For paginated PDFs, check if we need pagination or full file
        if file_instance.requires_pagination:
            user_role = get_user_role(request.user)

            # Instructors/admins without page_range get the full file
            if (
                user_role in [Role.ADMIN.value, Role.INSTRUCTOR.value]
                and not page_range_query
            ):
                return serve_whole_file(file_instance)

            # Use pagination service for page extraction
            pdf_service = PdfPaginationService()
            return pdf_service.serve_paginated_pdf(
                file_instance,
                request.user,
                page_range_query,
            )

        # For non-paginated files, serve the whole file
        return serve_whole_file(file_instance)


class GoogleFormLinkViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Google Form links.

    Provides role-based access to Google Form links:
    - Students: read-only access to active forms
    - Instructors: full CRUD access to all forms
    - Admins: full access (inherited)

    These links are global and shown to all users across all patient records.

    - List: GET /api/patients/google-forms/
    - Retrieve: GET /api/patients/google-forms/{id}/
    - Create: POST /api/patients/google-forms/ (instructors only)
    - Update: PUT/PATCH /api/patients/google-forms/{id}/ (instructors only)
    - Delete: DELETE /api/patients/google-forms/{id}/ (instructors only)

    Only active forms are returned by default for students.
    """

    queryset = GoogleFormLink.objects.all()
    serializer_class = GoogleFormLinkSerializer
    permission_classes: ClassVar[list[object]] = [GoogleFormLinkPermission]
    pagination_class = None  # Disable pagination for simple list of forms

    def get_queryset(self) -> QuerySet:
        """
        Return Google Form links based on user role:
        - Students: only active forms, ordered by display_order
        - Instructors/Admins: all forms, ordered by display_order
        """
        user_role = get_user_role(self.request.user)

        if user_role == Role.STUDENT.value:
            # Students only see active forms
            return GoogleFormLink.objects.filter(is_active=True).order_by(
                "display_order"
            )

        # Instructors and admins see all forms
        return GoogleFormLink.objects.all().order_by("display_order")
