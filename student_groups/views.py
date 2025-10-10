from .serializers import (
    ImagingRequestSerializer,
    BloodTestRequestSerializer,
    MedicationOrderSerializer,
    DischargeSummarySerializer,
    NoteSerializer,
    BloodPressureSerializer,
    HeartRateSerializer,
    BodyTemperatureSerializer,
    RespiratoryRateSerializer,
    BloodSugarSerializer,
    OxygenSaturationSerializer,
    PainScoreSerializer,
    ObservationsSerializer,
    ObservationDataSerializer,
)
from .models import (
    Note,
    BloodPressure,
    HeartRate,
    BodyTemperature,
    RespiratoryRate,
    BloodSugar,
    OxygenSaturation,
    PainScore,
    ObservationManager,
    ImagingRequest,
    BloodTestRequest,
    MedicationOrder,
    DischargeSummary,
)
from .pagination import ObservationsPagination
from core.permissions import ObservationPermission, LabRequestPermission
from core.context import ViewContext
from rest_framework.response import Response
from rest_framework import viewsets, status, mixins
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample


class ObservationsViewSet(viewsets.GenericViewSet):
    permission_classes = [ObservationPermission]
    serializer_class = ObservationsSerializer

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
                    }
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
    def create(self, request):
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
            if observation_type in data and data[observation_type]:
                data[observation_type]["user"] = request.user.id

        serializer = ObservationsSerializer(data=data)

        if serializer.is_valid():
            try:
                created_objects = serializer.save()
                return Response(created_objects, status=status.HTTP_201_CREATED)
            except Exception as e:
                return Response(
                    {"error": "Error occurred during creation", "detail": str(e)},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )
        else:
            return Response(
                {"error": "Data validation failed", "detail": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

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
    def list(self, request, *args, **kwargs):
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
                {"error": "patient_id is required"}, status=status.HTTP_400_BAD_REQUEST
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
            request.user.id, patient_id, ordering=ordering
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


class NoteViewSet(viewsets.ModelViewSet):
    queryset = Note.objects.all()
    serializer_class = NoteSerializer
    permission_classes = [ObservationPermission]

    def get_queryset(self):
        """Filter observations by authenticated user"""
        return Note.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class BloodPressureViewSet(viewsets.ModelViewSet):
    queryset = BloodPressure.objects.all()
    serializer_class = BloodPressureSerializer
    permission_classes = [ObservationPermission]

    def get_queryset(self):
        """Filter observations by authenticated user"""
        return BloodPressure.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class HeartRateViewSet(viewsets.ModelViewSet):
    queryset = HeartRate.objects.all()
    serializer_class = HeartRateSerializer
    permission_classes = [ObservationPermission]

    def get_queryset(self):
        """Filter observations by authenticated user"""
        return HeartRate.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class BodyTemperatureViewSet(viewsets.ModelViewSet):
    queryset = BodyTemperature.objects.all()
    serializer_class = BodyTemperatureSerializer
    permission_classes = [ObservationPermission]

    def get_queryset(self):
        """Filter observations by authenticated user"""
        return BodyTemperature.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class RespiratoryRateViewSet(viewsets.ModelViewSet):
    queryset = RespiratoryRate.objects.all()
    serializer_class = RespiratoryRateSerializer
    permission_classes = [ObservationPermission]

    def get_queryset(self):
        """Filter observations by authenticated user"""
        return RespiratoryRate.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class BloodSugarViewSet(viewsets.ModelViewSet):
    queryset = BloodSugar.objects.all()
    serializer_class = BloodSugarSerializer
    permission_classes = [ObservationPermission]

    def get_queryset(self):
        """Filter observations by authenticated user"""
        return BloodSugar.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class OxygenSaturationViewSet(viewsets.ModelViewSet):
    queryset = OxygenSaturation.objects.all()
    serializer_class = OxygenSaturationSerializer
    permission_classes = [ObservationPermission]

    def get_queryset(self):
        """Filter observations by authenticated user"""
        return OxygenSaturation.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class PainScoreViewSet(viewsets.ModelViewSet):
    queryset = PainScore.objects.all()
    serializer_class = PainScoreSerializer
    permission_classes = [ObservationPermission]

    def get_queryset(self):
        """Filter observations by authenticated user"""
        return PainScore.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class ImagingRequestViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    queryset = ImagingRequest.objects.all()
    serializer_class = ImagingRequestSerializer
    permission_classes = [LabRequestPermission]

    def get_serializer_context(self):
        context = super().get_serializer_context()
        if self.action == "create":
            context[ViewContext.STUDENT_CREATE.value] = True
        else:
            context[ViewContext.STUDENT_READ.value] = True
        return context

    def get_queryset(self):
        """Students can only see their own requests"""
        return ImagingRequest.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class BloodTestRequestViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    queryset = BloodTestRequest.objects.all()
    serializer_class = BloodTestRequestSerializer
    permission_classes = [LabRequestPermission]

    def get_queryset(self):
        """Students can only see their own requests"""
        return BloodTestRequest.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class MedicationOrderViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    queryset = MedicationOrder.objects.all()
    serializer_class = MedicationOrderSerializer
    permission_classes = [LabRequestPermission]

    def get_queryset(self):
        """Students can only see their own requests"""
        return MedicationOrder.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class DischargeSummaryViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    queryset = DischargeSummary.objects.all()
    serializer_class = DischargeSummarySerializer
    permission_classes = [LabRequestPermission]

    def get_queryset(self):
        """Students can only see their own requests"""
        return DischargeSummary.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
