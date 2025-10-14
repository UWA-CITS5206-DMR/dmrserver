from typing import Any, ClassVar

from django.core.exceptions import ValidationError
from django.db.models import QuerySet
from drf_spectacular.utils import OpenApiExample, OpenApiParameter, extend_schema
from rest_framework import mixins, status, viewsets
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.serializers import Serializer

from core.context import ViewContext
from core.permissions import LabRequestPermission, ObservationPermission

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
    BodyTemperatureSerializer,
    DischargeSummarySerializer,
    HeartRateSerializer,
    ImagingRequestSerializer,
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


class BaseStudentRequestViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    """
    Base ViewSet for student-side requests (lab requests and orders).

    Provides common functionality:
    - Automatic user filtering (students see only their requests)
    - Optional patient filtering via query parameter
    - Automatic user assignment in creation
    - LabRequestPermission enforcement
    - Read-only after creation (create, retrieve, list only)

    Subclasses only need to set: queryset, serializer_class

    Query Parameters:
    - patient: (optional) Filter requests by patient ID
    """

    permission_classes: ClassVar[list[Any]] = [LabRequestPermission]

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
        """List requests with optional patient filtering"""
        return super().list(request, *args, **kwargs)

    def get_queryset(self) -> QuerySet:
        """
        Filter requests by authenticated user and optionally by patient.

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


class ObservationsViewSet(viewsets.GenericViewSet):
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
        Retrieve all observations for a specific patient.

        This endpoint returns observations of various types (blood pressure,
        heart rate, body temperature, respiratory rate, blood sugar, oxygen
        saturation, pain score) for the specified patient.

        The authenticated user making the request is automatically extracted from
        the authentication token, and only observations recorded by that user are
        returned to ensure data privacy and isolation.

        Filtering and Pagination:
        - The results can be filtered by observation type using the `types` query
          parameter.
        - The number of results per page can be controlled using the `page_size`
          query parameter. By default, this is set to 10. The maximum allowed page
          size is 100.
        - Results are ordered by created_at in descending order (most recent first)
          by default. The ordering can be changed using the `ordering` query
          parameter. Supported values are `created_at` (ascending) and `-created_at`
          (descending).

        Query Parameters:
        - `patient_id`: (required) The ID of the patient whose observations are
          being requested.
        - `types`: (optional) A comma-separated list of observation types to
          filter by. Valid types are: blood_pressure, heart_rate, body_temperature,
          respiratory_rate, blood_sugar, oxygen_saturation, pain_score.
        - `page_size`: (optional) The number of results to return per page.
          Default is 10, maximum is 100.
        - `ordering`: (optional) The field to order results by. Supported values
          are `created_at` (ascending) and `-created_at` (descending). Default is
          `-created_at`.

        Returns:
        - `200 OK`: A paginated response with observation data following DRF
          standard pagination format:
          {
              "count": <total number of observation records across all types>,
              "next": null,
              "previous": null,
              "results": {
                  "blood_pressure": [...],
                  "heart_rate": [...],
                  ...
              }
          }
        - `400 Bad Request`: If the patient_id parameter is missing or invalid.
        - `403 Forbidden`: If the user does not have permission to view this
          patient's observations.

        Note:
        The `next` and `previous` fields are currently set to null because
        pagination across multiple observation types is complex. For full
        pagination support, use the individual observation type endpoints
        (e.g., /api/student-groups/blood-pressure/).
        """
        patient_id = request.query_params.get("patient_id")
        if not patient_id:
            return Response(
                {"detail": "patient_id is required"},
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


class ImagingRequestViewSet(BaseStudentRequestViewSet):
    """ViewSet for ImagingRequest (student-side)"""

    queryset = ImagingRequest.objects.all()
    serializer_class = ImagingRequestSerializer

    def get_serializer_context(self) -> dict:
        """Add context for student create/read operations"""
        context = super().get_serializer_context()
        if self.action == "create":
            context[ViewContext.STUDENT_CREATE.value] = True
        else:
            context[ViewContext.STUDENT_READ.value] = True
        return context


class BloodTestRequestViewSet(BaseStudentRequestViewSet):
    """ViewSet for BloodTestRequest (student-side)"""

    queryset = BloodTestRequest.objects.all()
    serializer_class = BloodTestRequestSerializer


class MedicationOrderViewSet(BaseStudentRequestViewSet):
    """ViewSet for MedicationOrder (student-side)"""

    queryset = MedicationOrder.objects.all()
    serializer_class = MedicationOrderSerializer


class DischargeSummaryViewSet(BaseStudentRequestViewSet):
    """ViewSet for DischargeSummary (student-side)"""

    queryset = DischargeSummary.objects.all()
    serializer_class = DischargeSummarySerializer
