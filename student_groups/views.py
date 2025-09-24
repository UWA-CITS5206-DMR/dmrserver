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
        description="Create one or more observation records (blood pressure, heart rate, body temperature, respiratory rate, blood sugar, oxygen saturation)",
        request=ObservationsSerializer,
        responses={201: ObservationDataSerializer},
        examples=[
            OpenApiExample(
                "Blood Pressure Only",
                value={
                    "blood_pressure": {
                        "patient": 1,
                        "user": 1,
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
                        "user": 1,
                        "systolic": 120,
                        "diastolic": 80,
                    },
                    "heart_rate": {"patient": 1, "user": 1, "heart_rate": 72},
                    "respiratory_rate": {
                        "patient": 1,
                        "user": 1,
                        "respiratory_rate": 16,
                    },
                    "blood_sugar": {"patient": 1, "user": 1, "sugar_level": 120.0},
                    "oxygen_saturation": {
                        "patient": 1,
                        "user": 1,
                        "saturation_percentage": 98,
                    },
                },
            ),
        ],
    )
    def create(self, request):
        serializer = ObservationsSerializer(data=request.data)

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
        description="Retrieve observations for a specific user and patient",
        parameters=[
            OpenApiParameter(
                name="user",
                type=int,
                location=OpenApiParameter.QUERY,
                required=True,
                description="User ID",
            ),
            OpenApiParameter(
                name="patient",
                type=int,
                location=OpenApiParameter.QUERY,
                required=True,
                description="Patient ID",
            ),
        ],
        responses={200: ObservationDataSerializer},
    )
    def list(self, request):
        user_id = request.query_params.get("user")
        patient_id = request.query_params.get("patient")

        if not user_id or not patient_id:
            return Response(
                {"error": "Both user and patient parameters are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            observations = ObservationManager.get_observations_by_user_and_patient(
                user_id, patient_id
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

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class BloodPressureViewSet(viewsets.ModelViewSet):
    queryset = BloodPressure.objects.all()
    serializer_class = BloodPressureSerializer
    permission_classes = [ObservationPermission]


class HeartRateViewSet(viewsets.ModelViewSet):
    queryset = HeartRate.objects.all()
    serializer_class = HeartRateSerializer
    permission_classes = [ObservationPermission]


class BodyTemperatureViewSet(viewsets.ModelViewSet):
    queryset = BodyTemperature.objects.all()
    serializer_class = BodyTemperatureSerializer
    permission_classes = [ObservationPermission]


class RespiratoryRateViewSet(viewsets.ModelViewSet):
    queryset = RespiratoryRate.objects.all()
    serializer_class = RespiratoryRateSerializer
    permission_classes = [ObservationPermission]


class BloodSugarViewSet(viewsets.ModelViewSet):
    queryset = BloodSugar.objects.all()
    serializer_class = BloodSugarSerializer
    permission_classes = [ObservationPermission]


class OxygenSaturationViewSet(viewsets.ModelViewSet):
    queryset = OxygenSaturation.objects.all()
    serializer_class = OxygenSaturationSerializer
    permission_classes = [ObservationPermission]


class PainScoreViewSet(viewsets.ModelViewSet):
    queryset = PainScore.objects.all()
    serializer_class = PainScoreSerializer
    permission_classes = [ObservationPermission]


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
