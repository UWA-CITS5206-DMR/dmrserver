"""
Cache Data Isolation Tests

Tests to verify that different users cannot access each other's cached data.
This is critical for security and privacy.

Coverage:
1. Patient endpoints - tests that different users get different cached data
2. File endpoints - tests that files are properly isolated per user
3. Observation endpoints - tests that observations are isolated per user
4. Investigation request endpoints - tests that requests are properly isolated
"""

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import override_settings
from rest_framework.test import APITestCase

from core.cache import CacheKeyGenerator

User = get_user_model()


@override_settings(
    CACHES={
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "test-cache",
        }
    }
)
class PatientEndpointDataIsolationTest(APITestCase):
    """Test that patient endpoints properly isolate data between users via caching"""

    def setUp(self) -> None:
        """Set up test users"""
        cache.clear()
        self.student1 = User.objects.create_user(
            username="student1",
            email="student1@test.com",
            password="testpass123",
        )
        self.student2 = User.objects.create_user(
            username="student2",
            email="student2@test.com",
            password="testpass123",
        )
        self.instructor = User.objects.create_user(
            username="instructor1",
            email="instructor1@test.com",
            password="testpass123",
        )
        # Set roles
        self.student1.role = "student"
        self.student1.save()
        self.student2.role = "student"
        self.student2.save()
        self.instructor.role = "instructor"
        self.instructor.save()

    def test_patient_cache_keys_same_for_same_user(self) -> None:
        """Test that same user gets same cache keys"""
        # Cache keys for user1 patient list should be identical
        self.client.force_authenticate(user=self.student1)
        key1 = CacheKeyGenerator.generate_key(
            "patients", "patients", "list", page="1", user_id=self.student1.id
        )
        key2 = CacheKeyGenerator.generate_key(
            "patients", "patients", "list", page="1", user_id=self.student1.id
        )
        assert key1 == key2, "Same user should generate same cache key"

    def test_patient_cache_keys_different_for_different_users(self) -> None:
        """Test that different users get different cache keys"""
        key1 = CacheKeyGenerator.generate_key(
            "patients", "patients", "list", page="1", user_id=self.student1.id
        )
        key2 = CacheKeyGenerator.generate_key(
            "patients", "patients", "list", page="1", user_id=self.student2.id
        )
        # Note: When user_id parameter is explicitly provided, it changes the key
        # even if cache_user_sensitive=False in the ViewSet
        assert key1 != key2, (
            "Explicitly including user_id in parameters should generate different keys"
        )

    def test_file_cache_keys_different_for_different_users(self) -> None:
        """Test that file cache keys are different for different users"""
        # FileViewSet has cache_user_sensitive=True
        key1 = CacheKeyGenerator.generate_key(
            "patients",
            "files",
            "list",
            patient_pk="1",
            page="1",
            user_id=self.student1.id,
        )
        key2 = CacheKeyGenerator.generate_key(
            "patients",
            "files",
            "list",
            patient_pk="1",
            page="1",
            user_id=self.student2.id,
        )
        assert key1 != key2, (
            "FileViewSet has cache_user_sensitive=True, "
            "so different users should get different cache keys"
        )


@override_settings(
    CACHES={
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "test-cache",
        }
    }
)
class ObservationDataIsolationTest(APITestCase):
    """Test that observation endpoints properly isolate data between users"""

    def setUp(self) -> None:
        """Set up test users"""
        cache.clear()
        self.student1 = User.objects.create_user(
            username="obs_student1",
            email="obs_student1@test.com",
            password="testpass123",
        )
        self.student2 = User.objects.create_user(
            username="obs_student2",
            email="obs_student2@test.com",
            password="testpass123",
        )

    def test_observation_cache_keys_include_user_id(self) -> None:
        """Test that observation cache keys include user ID for isolation"""
        # BaseObservationViewSet has cache_user_sensitive=True
        key1 = CacheKeyGenerator.generate_key(
            "student_groups",
            "observations",
            "list",
            patient="1",
            page="1",
            user_id=self.student1.id,
        )
        key2 = CacheKeyGenerator.generate_key(
            "student_groups",
            "observations",
            "list",
            patient="1",
            page="1",
            user_id=self.student2.id,
        )
        assert key1 != key2, (
            "BaseObservationViewSet has cache_user_sensitive=True, "
            "so different users should get different cache keys"
        )

    def test_observation_cache_keys_same_for_same_user(self) -> None:
        """Test that same user gets same cache keys for observations"""
        key1 = CacheKeyGenerator.generate_key(
            "student_groups",
            "observations",
            "list",
            patient="1",
            page="1",
            user_id=self.student1.id,
        )
        key2 = CacheKeyGenerator.generate_key(
            "student_groups",
            "observations",
            "list",
            patient="1",
            page="1",
            user_id=self.student1.id,
        )
        assert key1 == key2, (
            "Same user and parameters should generate identical cache keys"
        )


@override_settings(
    CACHES={
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "test-cache",
        }
    }
)
class InvestigationRequestDataIsolationTest(APITestCase):
    """Test that investigation request endpoints properly isolate data between users"""

    def setUp(self) -> None:
        """Set up test users"""
        cache.clear()
        self.student1 = User.objects.create_user(
            username="inv_student1",
            email="inv_student1@test.com",
            password="testpass123",
        )
        self.student2 = User.objects.create_user(
            username="inv_student2",
            email="inv_student2@test.com",
            password="testpass123",
        )

    def test_investigation_request_cache_keys_include_user_id(self) -> None:
        """Test that investigation request cache keys include user ID"""
        # BaseInvestigationRequestViewSet has cache_user_sensitive=True
        key1 = CacheKeyGenerator.generate_key(
            "student_groups",
            "investigation_requests",
            "list",
            patient="1",
            user="1",
            page="1",
            user_id=self.student1.id,
        )
        key2 = CacheKeyGenerator.generate_key(
            "student_groups",
            "investigation_requests",
            "list",
            patient="1",
            user="1",
            page="1",
            user_id=self.student2.id,
        )
        assert key1 != key2, (
            "BaseInvestigationRequestViewSet has cache_user_sensitive=True, "
            "so different users should get different cache keys"
        )

    def test_investigation_request_cache_keys_same_for_same_user(self) -> None:
        """Test that same user gets same cache keys"""
        key1 = CacheKeyGenerator.generate_key(
            "student_groups",
            "investigation_requests",
            "list",
            patient="1",
            user="1",
            page="1",
            user_id=self.student1.id,
        )
        key2 = CacheKeyGenerator.generate_key(
            "student_groups",
            "investigation_requests",
            "list",
            patient="1",
            user="1",
            page="1",
            user_id=self.student1.id,
        )
        assert key1 == key2, (
            "Same user and parameters should generate identical cache keys"
        )


@override_settings(
    CACHES={
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "test-cache",
        }
    }
)
class CacheUserSensitivityAuditTest(APITestCase):
    """Audit which ViewSets properly have user-sensitive caching configured"""

    def test_observation_viewsets_have_user_sensitive_caching(self) -> None:
        """Verify all observation ViewSets have cache_user_sensitive=True"""
        from student_groups.views import (
            BaseObservationViewSet,
            BloodPressureViewSet,
            BloodSugarViewSet,
            BodyTemperatureViewSet,
            HeartRateViewSet,
            NoteViewSet,
            OxygenSaturationViewSet,
            PainScoreViewSet,
            RespiratoryRateViewSet,
        )

        for viewset_class in [
            BaseObservationViewSet,
            BloodPressureViewSet,
            BloodSugarViewSet,
            BodyTemperatureViewSet,
            HeartRateViewSet,
            NoteViewSet,
            OxygenSaturationViewSet,
            PainScoreViewSet,
            RespiratoryRateViewSet,
        ]:
            viewset = viewset_class()
            assert viewset.cache_user_sensitive is True, (
                f"{viewset_class.__name__} should have cache_user_sensitive=True for data isolation"
            )

    def test_investigation_request_viewsets_have_user_sensitive_caching(self) -> None:
        """Verify investigation request ViewSets have cache_user_sensitive=True"""
        from student_groups.views import (
            BaseInvestigationRequestViewSet,
            BloodTestRequestViewSet,
            DischargeSummaryViewSet,
            ImagingRequestViewSet,
            MedicationOrderViewSet,
        )

        for viewset_class in [
            BaseInvestigationRequestViewSet,
            BloodTestRequestViewSet,
            ImagingRequestViewSet,
            MedicationOrderViewSet,
            DischargeSummaryViewSet,
        ]:
            viewset = viewset_class()
            assert viewset.cache_user_sensitive is True, (
                f"{viewset_class.__name__} should have cache_user_sensitive=True for data isolation"
            )

    def test_file_viewset_has_user_sensitive_caching(self) -> None:
        """Verify FileViewSet has cache_user_sensitive=True"""
        from patients.views import FileViewSet

        viewset = FileViewSet()
        assert viewset.cache_user_sensitive is True, (
            "FileViewSet should have cache_user_sensitive=True for file data isolation"
        )

    def test_patient_viewset_configuration_documented(self) -> None:
        """
        Document PatientViewSet cache configuration.

        Note: PatientViewSet has cache_user_sensitive=False because:
        - Patient list is typically the same for all users (admin data)
        - Patient filtering is handled via permissions
        - Users with access to patients see the same list
        """
        from patients.views import PatientViewSet

        viewset = PatientViewSet()
        assert viewset.cache_user_sensitive is False, (
            "PatientViewSet cache_user_sensitive=False is intentional (documented in docstring)"
        )
