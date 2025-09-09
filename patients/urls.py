from rest_framework_nested import routers

from .views import PatientViewSet, FileViewSet

router = routers.SimpleRouter()
router.register(r"patients", PatientViewSet)

files_router = routers.NestedSimpleRouter(router, r"patients", lookup="patient")
files_router.register(r"files", FileViewSet, basename="file")

urlpatterns = router.urls + files_router.urls
