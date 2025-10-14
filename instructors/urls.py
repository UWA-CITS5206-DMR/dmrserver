from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register(
    r"imaging-requests",
    views.ImagingRequestViewSet,
    basename="imaging-request",
)
router.register(
    r"blood-test-requests",
    views.BloodTestRequestViewSet,
    basename="blood-test-request",
)
router.register(r"dashboard", views.DashboardViewSet, basename="dashboard")

urlpatterns = [
    path("", include(router.urls)),
]
