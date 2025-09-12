from rest_framework import viewsets, mixins
from rest_framework.decorators import action
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema

from patients.models import Patient
from student_groups.models import LabRequest
from .serializers import (
    LabRequestSerializer,
    LabRequestStatusUpdateSerializer,
)
from core.permissions import InstructorOnlyPermission


class LabRequestViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """
    Instructor lab request management endpoints.
    Instructors can perform full CRUD operations on all lab requests.
    """

    queryset = LabRequest.objects.all()
    serializer_class = LabRequestSerializer
    permission_classes = [InstructorOnlyPermission]

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["for_instructor"] = True
        return context

    def get_serializer_class(self):
        if self.action in ["update", "partial_update"]:
            return LabRequestStatusUpdateSerializer
        return LabRequestSerializer

    @extend_schema(
        summary="List pending lab requests",
        description="Get all lab requests with pending status",
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
        summary="Get lab request statistics",
        description="Get counts of lab requests by status",
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

    permission_classes = [InstructorOnlyPermission]

    @extend_schema(
        summary="Get dashboard overview",
        description="Get overview statistics for instructor dashboard",
    )
    def list(self, request):
        data = {
            "patients_count": Patient.objects.count(),
            "total_lab_requests": LabRequest.objects.count(),
            "pending_lab_requests": LabRequest.objects.filter(status="pending").count(),
            "completed_lab_requests": LabRequest.objects.filter(
                status="completed"
            ).count(),
        }
        return Response(data)
