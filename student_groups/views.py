from django.shortcuts import render
from rest_framework import permissions, viewsets

from .models import Note, BloodPressure, HeartRate, BodyTemperature
from .serializers import (
    NoteSerializer,
    BloodPressureSerializer,
    HeartRateSerializer,
    BodyTemperatureSerializer,
)


class NoteViewSet(viewsets.ModelViewSet):
    queryset = Note.objects.all().order_by("-created_at")
    serializer_class = NoteSerializer
    permission_classes = [permissions.IsAuthenticated]


class BloodPressureViewSet(viewsets.ModelViewSet):
    queryset = BloodPressure.objects.all().order_by("-created_at")
    serializer_class = BloodPressureSerializer
    permission_classes = [permissions.IsAuthenticated]


class HeartRateViewSet(viewsets.ModelViewSet):
    queryset = HeartRate.objects.all().order_by("-created_at")
    serializer_class = HeartRateSerializer
    permission_classes = [permissions.IsAuthenticated]


class BodyTemperatureViewSet(viewsets.ModelViewSet):
    queryset = BodyTemperature.objects.all().order_by("-created_at")
    serializer_class = BodyTemperatureSerializer
    permission_classes = [permissions.IsAuthenticated]
