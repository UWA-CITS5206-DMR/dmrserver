from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    NoteViewSet,
    BloodPressureViewSet,
    HeartRateViewSet,
    BodyTemperatureViewSet,
    ObservationsViewSet,
)

router = DefaultRouter()
router.register(r"notes", NoteViewSet, basename="note")
router.register(
    r"observations/blood-pressures", BloodPressureViewSet, basename="blood-pressure"
)
router.register(r"observations/heart-rates", HeartRateViewSet, basename="heart-rate")
router.register(
    r"observations/body-temperatures",
    BodyTemperatureViewSet,
    basename="body-temperature",
)
router.register(r"observations", ObservationsViewSet, basename="observation")

urlpatterns = [
    path("", include(router.urls)),
]
