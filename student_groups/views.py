from typing import Any, ClassVar

from django.core.exceptions import ValidationError
from django.db.models import QuerySet
from drf_spectacular.utils import OpenApiExample, OpenApiParameter, extend_schema
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.serializers import Serializer

from core.context import Role, ViewContext
from core.permissions import (
    InvestigationRequestPermission,
    ObservationPermission,
    get_user_role,
)

from .models import (
    BloodPressure,
    BloodSugar,
    BloodTestRequest,
    BodyTemperature,
    DischargeSummary,
    HeartRate,
    ImagingRequest,
    MedicationOrder,
    Note,
    ObservationManager,
    OxygenSaturation,
    PainScore,
    RespiratoryRate,
)
from .pagination import ObservationsPagination
from .serializers import (
    BloodPressureSerializer,
    BloodSugarSerializer,
    BloodTestRequestSerializer,
    BloodTestRequestStatusUpdateSerializer,
    BodyTemperatureSerializer,
    DischargeSummarySerializer,
    HeartRateSerializer,
    ImagingRequestSerializer,
    ImagingRequestStatusUpdateSerializer,
    MedicationOrderSerializer,
    NoteSerializer,
    ObservationDataSerializer,
    ObservationsSerializer,
    OxygenSaturationSerializer,
    PainScoreSerializer,
    RespiratoryRateSerializer,
)


class BaseObservationViewSet(viewsets.ModelViewSet):
    """
    Base ViewSet for all observation types.

    Provides common functionality for observation ViewSets:
    - Automatic user filtering in get_queryset()
    - Optional patient filtering via query parameter
    - Automatic user assignment in perform_create()
    - ObservationPermission enforcement

    Subclasses only need to set:
    - queryset
    - serializer_class

    Query Parameters:
    - patient: (optional) Filter observations by patient ID
    """

    permission_classes: ClassVar[list[Any]] = [ObservationPermission]

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="patient",
                type=int,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Filter observations by patient ID",
            ),
        ],
    )
    def list(self, request: Request, *args: object, **kwargs: object) -> Response:
        """List observations with optional patient filtering"""
        return super().list(request, *args, **kwargs)

    def get_queryset(self) -> QuerySet:
        """
        Filter observations by authenticated user and optionally by patient.

        Always filters by user for security. If 'patient' query parameter
        is provided, additionally filters by patient ID.
        """
        queryset = self.queryset.filter(user=self.request.user)

        # Optional patient filtering
        patient_id = self.request.query_params.get("patient")
        if patient_id is not None:
            queryset = queryset.filter(patient_id=patient_id)

        return queryset

    def perform_create(self, serializer: Serializer) -> None:
        """Automatically set the user to the authenticated user"""
        serializer.save(user=self.request.user)


class BaseInvestigationRequestViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """Shared base for investigation requests across roles."""

    permission_classes: ClassVar[list[Any]] = [InvestigationRequestPermission]

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="patient",
                type=int,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Filter requests by patient ID",
            ),
        ],
    )
    def list(self, request: Request, *args: object, **kwargs: object) -> Response:
        """List requests with optional patient filtering."""
        return super().list(request, *args, **kwargs)

    def get_queryset(self) -> QuerySet:
        """Apply role-aware filtering for investigation requests."""
        queryset = self.queryset
        user_role = get_user_role(self.request.user)

        if user_role == Role.STUDENT.value:
            queryset = queryset.filter(user=self.request.user)
        elif user_role in {Role.INSTRUCTOR.value, Role.ADMIN.value}:
            pass  # Instructors and admins can see all requests
        else:
            return queryset.none()

        patient_param = self.request.query_params.get("patient")
        if patient_param is not None:
            try:
                patient_id = int(patient_param)
            except (TypeError, ValueError) as exc:
                raise DRFValidationError({"patient": "Invalid patient id"}) from exc
            queryset = queryset.filter(patient_id=patient_id)

        return queryset

    def get_serializer_context(self) -> dict[str, Any]:
        context = super().get_serializer_context()
        user_role = get_user_role(self.request.user)

        if user_role == Role.STUDENT.value:
            if self.action == "create":
                context[ViewContext.STUDENT_CREATE.value] = True
            else:
                context[ViewContext.STUDENT_READ.value] = True
        else:
            context[ViewContext.INSTRUCTOR_READ.value] = True

        return context

    def perform_create(self, serializer: Serializer) -> None:
        """Automatically set the user to the authenticated user."""
        serializer.save(user=self.request.user)


class ObservationsViewSet(viewsets.GenericViewSet):
    """ViewSet for bulk observation operations across all types."""

    permission_classes: ClassVar[list[Any]] = [ObservationPermission]
    serializer_class: ClassVar[Any] = ObservationsSerializer

    @extend_schema(
        summary="Create observations",
        description="Create one or more observation records. The user is automatically set to the authenticated user.",
        request=ObservationsSerializer,
        responses={201: ObservationDataSerializer},
        examples=[
            OpenApiExample(
                "Blood Pressure Only",
                value={
                    "blood_pressure": {
                        "patient": 1,
                        "systolic": 120,
                        "diastolic": 80,
                    },
                },
            ),
            OpenApiExample(
                "Multiple Observations",
                value={
                    "blood_pressure": {
                        "patient": 1,
                        "systolic": 120,
                        "diastolic": 80,
                    },
                    "heart_rate": {"patient": 1, "heart_rate": 72},
                    "respiratory_rate": {
                        "patient": 1,
                        "respiratory_rate": 16,
                    },
                    "blood_sugar": {"patient": 1, "sugar_level": 120.0},
                    "oxygen_saturation": {
                        "patient": 1,
                        "saturation_percentage": 98,
                    },
                },
            ),
        ],
    )
    def create(self, request: Request) -> Response:
        # Inject the authenticated user into each observation type
        data = request.data.copy()
        for observation_type in [
            "blood_pressure",
            "heart_rate",
            "body_temperature",
            "respiratory_rate",
            "blood_sugar",
            "oxygen_saturation",
            "pain_score",
        ]:
            if data.get(observation_type):
                data[observation_type]["user"] = request.user.id

        serializer = ObservationsSerializer(data=data)

        if serializer.is_valid():
            try:
                created_objects = serializer.save()
            except ValidationError as e:
                # Use DRF standard 'detail' for error messages
                return Response(
                    {"detail": e.message},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            except Exception as e:  # noqa: BLE001  (fallback for unexpected errors)
                return Response(
                    {"detail": str(e)},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )
            return Response(created_objects, status=status.HTTP_201_CREATED)
        # Return serializer.errors directly under standard validation response
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        summary="List observations",
        description=(
            "Retrieve observations for the authenticated user and a specific patient. "
            "Supports ordering and basic pagination via page_size parameter. "
            "\n\nNote: This endpoint returns multiple heterogeneous observation types in a single response, "
            "which doesn't support standard DRF pagination (page numbers, next/previous links). "
            "For full pagination support with individual observation types, use the specific endpoints: "
            "/observations/blood-pressures/, /observations/heart-rates/, etc."
        ),
        parameters=[
            OpenApiParameter(
                name="patient",
                type=int,
                location=OpenApiParameter.QUERY,
                required=True,
                description="Patient ID",
            ),
            OpenApiParameter(
                name="ordering",
                type=str,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Order by field (e.g., 'created_at' or '-created_at' for descending). Default: '-created_at'",
            ),
            OpenApiParameter(
                name="page_size",
                type=int,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Limit number of records returned for each observation type. Does not support page navigation.",
            ),
        ],
        responses={200: ObservationDataSerializer},
    )
    def list(self, request: Request, *_args: object, **_kwargs: object) -> Response:
        """
        Retrieve all observations for a specific patient across all observation types.

        Returns observations grouped by type (blood_pressure, heart_rate, etc.).
        Only shows observations created by the authenticated user for privacy.

        Query Parameters:
        - patient (required): Patient ID
        - types (optional): Comma-separated list of observation types to filter
        - page_size (optional): Number of records per type (default: 10, max: 100)
        - ordering (optional): 'created_at' or '-created_at' (default: '-created_at')

        Returns paginated response with observations grouped by type.
        Note: Full pagination support available via individual type endpoints.
        """
        patient_id = request.query_params.get("patient")
        if not patient_id:
            return Response(
                {"detail": "patient is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Get page_size parameter with validation
        try:
            page_size = int(request.query_params.get("page_size", 10))
            # Limit maximum page_size to prevent excessive data retrieval
            page_size = min(max(page_size, 1), 100)  # Between 1 and 100
        except (ValueError, TypeError):
            page_size = 10  # Default to 10 if invalid value provided

        # Get ordering parameter (default to -created_at for most recent first)
        ordering = request.query_params.get("ordering", "-created_at")
        # Validate ordering parameter
        if ordering not in ["created_at", "-created_at"]:
            ordering = "-created_at"  # Default to descending if invalid value

        # Get observations with ordering
        observations = ObservationManager.get_observations_by_user_and_patient(
            request.user.id,
            patient_id,
            ordering=ordering,
        )

        # Apply pagination (slicing) to each observation type
        paginated_observations = {}
        for obs_type, obs_list in observations.items():
            paginated_observations[obs_type] = obs_list[:page_size]

        # Serialize the data using ObservationDataSerializer (designed for list output)
        serializer = ObservationDataSerializer(paginated_observations)

        # Use custom pagination class to wrap in standard DRF format
        paginator = ObservationsPagination()
        # Calculate total count across all observation types
        total_count = sum(len(obs_list) for obs_list in observations.values())
        paginator.total_count = total_count
        return paginator.get_paginated_response(serializer.data)


class NoteViewSet(BaseObservationViewSet):
    """ViewSet for Note observations"""

    queryset = Note.objects.all()
    serializer_class = NoteSerializer


class BloodPressureViewSet(BaseObservationViewSet):
    """ViewSet for BloodPressure observations"""

    queryset = BloodPressure.objects.all()
    serializer_class = BloodPressureSerializer


class HeartRateViewSet(BaseObservationViewSet):
    """ViewSet for HeartRate observations"""

    queryset = HeartRate.objects.all()
    serializer_class = HeartRateSerializer


class BodyTemperatureViewSet(BaseObservationViewSet):
    """ViewSet for BodyTemperature observations"""

    queryset = BodyTemperature.objects.all()
    serializer_class = BodyTemperatureSerializer


class RespiratoryRateViewSet(BaseObservationViewSet):
    """ViewSet for RespiratoryRate observations"""

    queryset = RespiratoryRate.objects.all()
    serializer_class = RespiratoryRateSerializer


class BloodSugarViewSet(BaseObservationViewSet):
    """ViewSet for BloodSugar observations"""

    queryset = BloodSugar.objects.all()
    serializer_class = BloodSugarSerializer


class OxygenSaturationViewSet(BaseObservationViewSet):
    """ViewSet for OxygenSaturation observations"""

    queryset = OxygenSaturation.objects.all()
    serializer_class = OxygenSaturationSerializer


class PainScoreViewSet(BaseObservationViewSet):
    """ViewSet for PainScore observations"""

    queryset = PainScore.objects.all()
    serializer_class = PainScoreSerializer


class ImagingRequestViewSet(BaseInvestigationRequestViewSet):
    """Unified imaging request API for students and instructors."""

    queryset = ImagingRequest.objects.select_related("user", "patient")
    serializer_class = ImagingRequestSerializer

    def get_serializer_class(self) -> type[Serializer]:
        if self.action in {"update", "partial_update"}:
            return ImagingRequestStatusUpdateSerializer
        return super().get_serializer_class()

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
        queryset = self.get_queryset().filter(status="pending")

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @extend_schema(
        summary="Get imaging request statistics",
        description="Get counts of imaging requests by status",
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
        queryset = self.get_queryset()

        stats = {
            "total": queryset.count(),
            "pending": queryset.filter(status="pending").count(),
            "completed": queryset.filter(status="completed").count(),
        }
        return Response(stats)


class BloodTestRequestViewSet(BaseInvestigationRequestViewSet):
    """Unified blood test request API for students and instructors."""

    queryset = BloodTestRequest.objects.select_related("user", "patient")
    serializer_class = BloodTestRequestSerializer

    def get_serializer_class(self) -> type[Serializer]:
        if self.action in {"update", "partial_update"}:
            return BloodTestRequestStatusUpdateSerializer
        return super().get_serializer_class()

    @extend_schema(
        summary="List pending blood test requests",
        description="Get all blood test requests with pending status",
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
        queryset = self.get_queryset().filter(status="pending")

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @extend_schema(
        summary="Get blood test request statistics",
        description="Get counts of blood test requests by status",
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
        queryset = self.get_queryset()

        stats = {
            "total": queryset.count(),
            "pending": queryset.filter(status="pending").count(),
            "completed": queryset.filter(status="completed").count(),
        }
        return Response(stats)


class MedicationOrderViewSet(BaseInvestigationRequestViewSet):
    """ViewSet for MedicationOrder (student-side)"""

    queryset = MedicationOrder.objects.all()
    serializer_class = MedicationOrderSerializer


class DischargeSummaryViewSet(BaseInvestigationRequestViewSet):
    """ViewSet for DischargeSummary (student-side)"""

    queryset = DischargeSummary.objects.all()
    serializer_class = DischargeSummarySerializer
