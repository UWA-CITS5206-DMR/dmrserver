from drf_spectacular.utils import extend_schema
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
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


class ImagingRequestViewSet(
    mixins.CreateModelMixin,
    mixins.DestroyModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    queryset = ImagingRequest.objects.select_related("user", "patient").all()
    serializer_class = ImagingRequestSerializer
    permission_classes = [InstructorManagementPermission]

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context[ViewContext.INSTRUCTOR_READ.value] = True
        return context

    def get_serializer_class(self):
        if self.action in ["update", "partial_update"]:
            return ImagingRequestStatusUpdateSerializer
        return ImagingRequestSerializer

    @extend_schema(
        summary="List pending imaging requests",
        description="Get all imaging requests with pending status",
    )
    @action(detail=False, methods=["get"])
    def pending(self, request):
        pending_requests = self.queryset.filter(status="pending")
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
    @action(detail=False, methods=["get"])
    def stats(self, request):
        stats = {
            "total": self.queryset.count(),
            "pending": self.queryset.filter(status="pending").count(),
            "completed": self.queryset.filter(status="completed").count(),
        }
        return Response(stats)


class BloodTestRequestViewSet(
    mixins.CreateModelMixin,
    mixins.DestroyModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    queryset = BloodTestRequest.objects.select_related("user", "patient").all()
    serializer_class = BloodTestRequestSerializer
    permission_classes = [InstructorManagementPermission]

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context[ViewContext.INSTRUCTOR_READ.value] = True
        return context

    def get_serializer_class(self):
        if self.action in ["update", "partial_update"]:
            return BloodTestRequestStatusUpdateSerializer
        return BloodTestRequestSerializer

    @extend_schema(
        summary="List pending blood test requests",
        description="Get all blood test requests with pending status",
    )
    @action(detail=False, methods=["get"])
    def pending(self, request):
        pending_requests = self.queryset.filter(status="pending")
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
    @action(detail=False, methods=["get"])
    def stats(self, request):
        stats = {
            "total": self.queryset.count(),
            "pending": self.queryset.filter(status="pending").count(),
            "completed": self.queryset.filter(status="completed").count(),
        }
        return Response(stats)


class DashboardViewSet(viewsets.GenericViewSet):
    """
    Instructor dashboard data endpoints.
    """

    permission_classes = [InstructorManagementPermission]

    @extend_schema(
        summary="Get dashboard overview",
        description="Get overview statistics for instructor dashboard",
    )
    def list(self, request):
        data = {
            "patients_count": Patient.objects.count(),
            "total_imaging_requests": ImagingRequest.objects.count(),
            "pending_imaging_requests": ImagingRequest.objects.filter(
                status="pending"
            ).count(),
            "completed_imaging_requests": ImagingRequest.objects.filter(
                status="completed"
            ).count(),
            "total_blood_test_requests": BloodTestRequest.objects.count(),
            "pending_blood_test_requests": BloodTestRequest.objects.filter(
                status="pending"
            ).count(),
            "completed_blood_test_requests": BloodTestRequest.objects.filter(
                status="completed"
            ).count(),
        }
        return Response(data)
