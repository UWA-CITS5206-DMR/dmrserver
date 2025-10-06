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
from core.permissions import ObservationPermission, IsStudent
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
    def list(self, request):
        """
        List all observation types for a patient.
        
        Note: This endpoint uses manual pagination with page_size parameter instead of
        standard DRF pagination because it returns a dictionary of multiple heterogeneous
        observation types. Standard DRF pagination is designed for single querysets.
        
        For proper paginated access to individual observation types, use:
        - GET /api/student-groups/observations/blood-pressures/
        - GET /api/student-groups/observations/heart-rates/
        etc. These endpoints support full DRF pagination.
        """
        # Automatically use the authenticated user
        user_id = request.user.id
        patient_id = request.query_params.get("patient")
        ordering = request.query_params.get("ordering", "-created_at")
        page_size = request.query_params.get("page_size")

        if not patient_id:
            return Response(
                {"error": "Patient parameter is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            # Get observations with ordering
            observations = ObservationManager.get_observations_by_user_and_patient(
                user_id, patient_id, ordering=ordering
            )

            # Apply page_size limit if specified
            # Note: This is manual slicing, not standard DRF pagination
            if page_size:
                try:
                    page_size = int(page_size)
                    for key in observations:
                        observations[key] = observations[key][:page_size]
                except (ValueError, TypeError):
                    return Response(
                        {"error": "Invalid page_size parameter"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

            result_serializer = ObservationDataSerializer(instance=observations)

            return Response(result_serializer.data, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {"error": "Error occurred during query", "detail": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


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
    permission_classes = [IsStudent]

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
    permission_classes = [IsStudent]

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
    permission_classes = [IsStudent]

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
    permission_classes = [IsStudent]

    def get_queryset(self):
        """Students can only see their own requests"""
        return DischargeSummary.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
