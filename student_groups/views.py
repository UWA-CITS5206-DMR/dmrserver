from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample
from .models import Note, BloodPressure, HeartRate, BodyTemperature, ObservationManager
from .serializers import (
    NoteSerializer,
    BloodPressureSerializer,
    HeartRateSerializer,
    BodyTemperatureSerializer,
    ObservationsSerializer,
    ObservationDataSerializer,
)


class ObservationsViewSet(viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = ObservationsSerializer

    @extend_schema(
        summary="Create observations",
        description="Create one or more observation records (blood pressure, heart rate, body temperature)",
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
    permission_classes = [IsAuthenticated]


class BloodPressureViewSet(viewsets.ModelViewSet):
    queryset = BloodPressure.objects.all()
    serializer_class = BloodPressureSerializer
    permission_classes = [IsAuthenticated]


class HeartRateViewSet(viewsets.ModelViewSet):
    queryset = HeartRate.objects.all()
    serializer_class = HeartRateSerializer
    permission_classes = [IsAuthenticated]


class BodyTemperatureViewSet(viewsets.ModelViewSet):
    queryset = BodyTemperature.objects.all()
    serializer_class = BodyTemperatureSerializer
    permission_classes = [IsAuthenticated]
