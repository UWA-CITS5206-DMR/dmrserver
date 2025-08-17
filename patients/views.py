from rest_framework import permissions, viewsets

from .models import Patient, File
from .serializers import PatientSerializer, FileSerializer


class PatientViewSet(viewsets.ModelViewSet):
    queryset = Patient.objects.all().order_by("-created_at")
    serializer_class = PatientSerializer
    permission_classes = [permissions.IsAuthenticated]


class FileViewSet(viewsets.ModelViewSet):
    queryset = File.objects.all().order_by("-created_at")
    serializer_class = FileSerializer
    permission_classes = [permissions.IsAuthenticated]
