from rest_framework import permissions, viewsets

from .models import Patient, BloodPressure, LabTest
from .serializers import PatientSerializer, BloodPressureSerializer, LabTestSerializer


class PatientViewSet(viewsets.ModelViewSet):
    queryset = Patient.objects.all().order_by("-created_at")
    serializer_class = PatientSerializer
    permission_classes = [permissions.IsAuthenticated]


class BloodPressureViewSet(viewsets.ModelViewSet):
    queryset = BloodPressure.objects.all().order_by("-measurement_date")
    serializer_class = BloodPressureSerializer
    permission_classes = [permissions.IsAuthenticated]


class LabTestViewSet(viewsets.ModelViewSet):
    queryset = LabTest.objects.all().order_by("-test_date")
    serializer_class = LabTestSerializer
    permission_classes = [permissions.IsAuthenticated]
