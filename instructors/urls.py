from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register(r"student-groups", views.StudentGroupViewSet, basename="student-group")

urlpatterns = [
    path("", include(router.urls)),
]
