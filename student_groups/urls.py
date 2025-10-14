from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    BloodPressureViewSet,
    BloodSugarViewSet,
    BloodTestRequestViewSet,
    BodyTemperatureViewSet,
    DischargeSummaryViewSet,
    HeartRateViewSet,
    ImagingRequestViewSet,
    MedicationOrderViewSet,
    NoteViewSet,
    ObservationsViewSet,
    OxygenSaturationViewSet,
    PainScoreViewSet,
    RespiratoryRateViewSet,
)

router = DefaultRouter()
router.register(r"notes", NoteViewSet, basename="note")
router.register(
    r"observations/blood-pressures",
    BloodPressureViewSet,
    basename="blood-pressure",
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
router.register(r"imaging-requests", ImagingRequestViewSet, basename="imaging-request")
router.register(
    r"blood-test-requests",
    BloodTestRequestViewSet,
    basename="blood-test-request",
)
router.register(
    r"medication-orders",
    MedicationOrderViewSet,
    basename="medication-order",
)
router.register(
    r"discharge-summaries",
    DischargeSummaryViewSet,
    basename="discharge-summary",
)

urlpatterns = [
    path("", include(router.urls)),
]
