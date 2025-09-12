from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    NoteViewSet,
    BloodPressureViewSet,
    HeartRateViewSet,
    BodyTemperatureViewSet,
    RespiratoryRateViewSet,
    BloodSugarViewSet,
    OxygenSaturationViewSet,
    PainScoreViewSet,
    ObservationsViewSet,
    LabRequestViewSet,
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
router.register(
    r"observations/respiratory-rates",
    RespiratoryRateViewSet,
    basename="respiratory-rate",
)
router.register(
    r"observations/blood-sugars",
    BloodSugarViewSet,
    basename="blood-sugar",
)
router.register(
    r"observations/oxygen-saturations",
    OxygenSaturationViewSet,
    basename="oxygen-saturation",
)
router.register(
    r"observations/pain-scores",
    PainScoreViewSet,
    basename="pain-score",
)
router.register(r"observations", ObservationsViewSet, basename="observation")
router.register(r"lab-requests", LabRequestViewSet, basename="lab-request")

urlpatterns = [
    path("", include(router.urls)),
]
