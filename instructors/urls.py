from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r"lab-requests", views.LabRequestViewSet, basename="lab-request")
router.register(r"dashboard", views.DashboardViewSet, basename="dashboard")

urlpatterns = [
    path("", include(router.urls)),
]
