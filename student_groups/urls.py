from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    NoteViewSet,
    BloodPressureViewSet,
    HeartRateViewSet,
    BodyTemperatureViewSet,
)

router = DefaultRouter()
router.register(r"notes", NoteViewSet)
router.register(r"blood-pressures", BloodPressureViewSet)
router.register(r"heart-rates", HeartRateViewSet)
router.register(r"body-temperatures", BodyTemperatureViewSet)

urlpatterns = [
    path("", include(router.urls)),
]
