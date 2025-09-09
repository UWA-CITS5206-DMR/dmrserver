from rest_framework import viewsets, status, mixins
from rest_framework.decorators import action
from rest_framework.response import Response
from core.permissions import PatientPermission

from .models import Patient, File
from .serializers import PatientSerializer, FileSerializer


class FileViewSet(
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    queryset = File.objects.none()
    serializer_class = FileSerializer
    permission_classes = [PatientPermission]

    def get_queryset(self):
        return File.objects.filter(patient_id=self.kwargs["patient_pk"])


class PatientViewSet(viewsets.ModelViewSet):
    queryset = Patient.objects.all()
    serializer_class = PatientSerializer
    permission_classes = [PatientPermission]

    @action(detail=True, methods=["post"], serializer_class=FileSerializer)
    def upload_file(self, request, pk=None):
        patient = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(patient=patient)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
