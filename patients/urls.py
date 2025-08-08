from django.urls import path, include
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register(r"patients", views.PatientViewSet)
router.register(r"blood-pressures", views.BloodPressureViewSet)
router.register(r"lab-tests", views.LabTestViewSet)

urlpatterns = [
    path("api/", include(router.urls)),
]
