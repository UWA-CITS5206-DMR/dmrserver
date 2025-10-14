from typing import Any, ClassVar

from django.db.models import QuerySet
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.request import Request
from rest_framework.response import Response

from core.context import ViewContext
from core.permissions import InstructorManagementPermission
from patients.models import Patient
from student_groups.models import BloodTestRequest, ImagingRequest

from .serializers import (
    BloodTestRequestSerializer,
    BloodTestRequestStatusUpdateSerializer,
    ImagingRequestSerializer,
    ImagingRequestStatusUpdateSerializer,
)


class BaseInstructorRequestViewSet(
    mixins.CreateModelMixin,
    mixins.DestroyModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """
    Base ViewSet for instructor-side requests (lab requests and imaging).

    Provides common functionality:
    - Instructor permission enforcement
    - Optional patient filtering via query parameter ('patient' or 'patient_id')
    - Automatic user assignment in creation (saves `user=self.request.user`)
    """

    permission_classes: ClassVar[list[Any]] = [InstructorManagementPermission]

    def get_queryset(self) -> QuerySet:
        """Return the base queryset, optionally filtered by patient id."""
        queryset = self.queryset
        patient_id = self.request.query_params.get(
            "patient"
        ) or self.request.query_params.get("patient_id")
        if patient_id is None:
            return queryset
        try:
            pid = int(patient_id)
        except (ValueError, TypeError):
            raise DRFValidationError({"patient": "Invalid patient id"}) from None
        return queryset.filter(patient_id=pid)

    def perform_create(self, serializer: object) -> None:
        """Automatically set the user to the authenticated user on create."""
        serializer.save(user=self.request.user)


class ImagingRequestViewSet(BaseInstructorRequestViewSet):
    queryset = ImagingRequest.objects.select_related("user", "patient").all()
    serializer_class = ImagingRequestSerializer

    def get_serializer_context(self) -> dict:
        context = super().get_serializer_context()
        context[ViewContext.INSTRUCTOR_READ.value] = True
        return context

    def get_serializer_class(self) -> type:
        if self.action in ["update", "partial_update"]:
            return ImagingRequestStatusUpdateSerializer
        return ImagingRequestSerializer

    @extend_schema(
        summary="List pending imaging requests",
        description="Get all imaging requests with pending status",
        parameters=[
            OpenApiParameter(
                name="patient",
                type=int,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Filter imaging requests by patient ID",
            ),
        ],
    )
    @action(detail=False, methods=["get"])
    def pending(self, _request: Request) -> Response:
        # Use get_queryset so optional patient filtering is applied
        pending_requests = self.get_queryset().filter(status="pending")
        page = self.paginate_queryset(pending_requests)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(pending_requests, many=True)
        return Response(serializer.data)

    @extend_schema(
        summary="Get imaging request statistics",
        description="Get counts of imaging requests by status",
    )
    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="patient",
                type=int,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Filter imaging requests by patient ID",
            ),
        ],
    )
    @action(detail=False, methods=["get"])
    def stats(self, _request: Request) -> Response:
        qs = self.get_queryset()
        stats = {
            "total": qs.count(),
            "pending": qs.filter(status="pending").count(),
            "completed": qs.filter(status="completed").count(),
        }
        return Response(stats)

    # Inherits get_queryset and perform_create behavior from BaseInstructorRequestViewSet


class BloodTestRequestViewSet(BaseInstructorRequestViewSet):
    queryset = BloodTestRequest.objects.select_related("user", "patient").all()
    serializer_class = BloodTestRequestSerializer

    def get_serializer_context(self) -> dict:
        context = super().get_serializer_context()
        context[ViewContext.INSTRUCTOR_READ.value] = True
        return context

    def get_serializer_class(self) -> type:
        if self.action in ["update", "partial_update"]:
            return BloodTestRequestStatusUpdateSerializer
        return BloodTestRequestSerializer

    @extend_schema(
        summary="List pending blood test requests",
        description="Get all blood test requests with pending status",
    )
    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="patient",
                type=int,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Filter blood test requests by patient ID",
            ),
        ],
    )
    @action(detail=False, methods=["get"])
    def pending(self, _request: Request) -> Response:
        pending_requests = self.get_queryset().filter(status="pending")
        page = self.paginate_queryset(pending_requests)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(pending_requests, many=True)
        return Response(serializer.data)

    @extend_schema(
        summary="Get blood test request statistics",
        description="Get counts of blood test requests by status",
    )
    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="patient",
                type=int,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Filter blood test requests by patient ID",
            ),
        ],
    )
    @action(detail=False, methods=["get"])
    def stats(self, _request: Request) -> Response:
        qs = self.get_queryset()
        stats = {
            "total": qs.count(),
            "pending": qs.filter(status="pending").count(),
            "completed": qs.filter(status="completed").count(),
        }
        return Response(stats)

    # Inherits get_queryset and perform_create behavior from BaseInstructorRequestViewSet


class DashboardViewSet(viewsets.GenericViewSet):
    """
    Instructor dashboard data endpoints.
    """

    permission_classes: ClassVar[list[Any]] = [InstructorManagementPermission]

    @extend_schema(
        summary="Get dashboard overview",
        description="Get overview statistics for instructor dashboard",
    )
    def list(self, _request: object) -> Response:
        data = {
            "patients_count": Patient.objects.count(),
            "total_imaging_requests": ImagingRequest.objects.count(),
            "pending_imaging_requests": ImagingRequest.objects.filter(
                status="pending",
            ).count(),
            "completed_imaging_requests": ImagingRequest.objects.filter(
                status="completed",
            ).count(),
            "total_blood_test_requests": BloodTestRequest.objects.count(),
            "pending_blood_test_requests": BloodTestRequest.objects.filter(
                status="pending",
            ).count(),
            "completed_blood_test_requests": BloodTestRequest.objects.filter(
                status="completed",
            ).count(),
        }
        return Response(data)
