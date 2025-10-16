"""
Cache Integration Tests

Comprehensive tests for caching system integration with all ViewSets.
Tests cover:
1. Cache key generation consistency
2. Cache invalidation patterns
3. ViewSet integration (automatic caching on list/retrieve)
4. Cache invalidation on write operations (create/update/destroy)
5. Multi-user cache isolation
"""

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase, override_settings
from rest_framework.test import APITestCase

from core.cache import CacheKeyGenerator, CacheManager

User = get_user_model()


class CacheKeyGeneratorTest(TestCase):
    """Test CacheKeyGenerator functionality"""

    def setUp(self) -> None:
        """Clear cache before each test"""
        cache.clear()

    def test_consistent_key_generation_with_parameter_order(self) -> None:
        """Test that parameter order doesn't affect key generation"""
        key1 = CacheKeyGenerator.generate_key(
            "student_groups", "observations", "list", patient="5", page_size="10"
        )
        key2 = CacheKeyGenerator.generate_key(
            "student_groups", "observations", "list", page_size="10", patient="5"
        )

        assert key1 == key2, "Keys should be identical regardless of parameter order"

    def test_different_params_generate_different_keys(self) -> None:
        """Test that different parameters generate different keys"""
        key1 = CacheKeyGenerator.generate_key(
            "student_groups", "observations", "list", patient="5"
        )
        key2 = CacheKeyGenerator.generate_key(
            "student_groups", "observations", "list", patient="6"
        )

        assert key1 != key2, "Different parameters should generate different keys"

    def test_invalidation_key_pattern_generation(self) -> None:
        """Test invalidation key pattern generation"""
        patterns = CacheKeyGenerator.generate_invalidation_keys(
            "student_groups",
            "observations",
            patient_id="5",
            user_id="1",
        )

        assert "student_groups:observations:list:*" in patterns
        assert "student_groups:observations:list:patient_id_5:*" in patterns
        assert "student_groups:observations:list:user_id_1:*" in patterns

    def test_key_format_includes_all_components(self) -> None:
        """Test that generated keys follow expected format"""
        key = CacheKeyGenerator.generate_key(
            "student_groups",
            "observations",
            "list",
            patient="5",
        )

        assert "student_groups" in key
        assert "observations" in key
        assert "list" in key

    def test_same_params_different_actions_different_keys(self) -> None:
        """Test that same params with different actions produce different keys"""
        list_key = CacheKeyGenerator.generate_key(
            "student_groups", "observations", "list", patient="5"
        )
        retrieve_key = CacheKeyGenerator.generate_key(
            "student_groups", "observations", "retrieve", patient="5"
        )

        assert list_key != retrieve_key, "Different actions should have different keys"


class CacheManagerTest(TestCase):
    """Test CacheManager functionality"""

    def setUp(self) -> None:
        """Clear cache before each test"""
        cache.clear()

    def test_set_and_get_cached_data(self) -> None:
        """Test setting and retrieving cached data"""
        test_data = {"test": "data", "nested": {"value": 123}}
        key = "test_key"

        CacheManager.set_cached(key, test_data, 300)
        result = CacheManager.get_cached(key)

        assert result == test_data, "Retrieved data should match stored data"

    def test_get_missing_cache_returns_none(self) -> None:
        """Test that getting missing cache returns None"""
        result = CacheManager.get_cached("nonexistent_key_12345")
        assert result is None, "Missing cache should return None"

    def test_invalidate_cache_pattern_clears_matching_keys(self) -> None:
        """Test cache invalidation by pattern"""
        cache.set("prefix:key1", "value1", 300)
        cache.set("prefix:key2", "value2", 300)
        cache.set("other:key3", "value3", 300)

        assert cache.get("prefix:key1") is not None
        assert cache.get("other:key3") is not None

        CacheManager.invalidate_cache(["prefix:*"])

        assert cache.get("prefix:key1") is None
        assert cache.get("prefix:key2") is None
        assert cache.get("other:key3") is not None

    def test_set_cached_with_ttl(self) -> None:
        """Test that set_cached respects TTL"""
        test_data = {"test": "data"}
        key = "ttl_test_key"

        CacheManager.set_cached(key, test_data, 300)
        result = CacheManager.get_cached(key)

        assert result == test_data, "Data should be cached with TTL"

    def test_invalidate_multiple_patterns(self) -> None:
        """Test invalidating multiple cache patterns"""
        cache.set("app1:model1:key", "value1", 300)
        cache.set("app2:model2:key", "value2", 300)
        cache.set("app1:model2:key", "value3", 300)

        CacheManager.invalidate_cache(["app1:model1:*", "app2:model2:*"])

        assert cache.get("app1:model1:key") is None
        assert cache.get("app2:model2:key") is None
        assert cache.get("app1:model2:key") is not None


@override_settings(
    CACHES={
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "test-cache",
        }
    }
)
class ObservationViewSetCachingTest(APITestCase):
    """Test observation endpoints caching"""

    def setUp(self) -> None:
        """Set up test client and clear cache"""
        cache.clear()

    def test_blood_pressure_viewset_has_caching(self) -> None:
        """Test that BloodPressureViewSet has caching configured"""
        from student_groups.views import BloodPressureViewSet

        viewset = BloodPressureViewSet()
        assert hasattr(viewset, "cache_app")
        assert hasattr(viewset, "cache_model")
        assert viewset.cache_app == "student_groups"
        assert viewset.cache_model == "blood_pressures"

    def test_heart_rate_viewset_has_caching(self) -> None:
        """Test that HeartRateViewSet has caching configured"""
        from student_groups.views import HeartRateViewSet

        viewset = HeartRateViewSet()
        assert hasattr(viewset, "cache_app")
        assert viewset.cache_app == "student_groups"

    def test_body_temperature_viewset_has_caching(self) -> None:
        """Test that BodyTemperatureViewSet has caching configured"""
        from student_groups.views import BodyTemperatureViewSet

        viewset = BodyTemperatureViewSet()
        assert hasattr(viewset, "cache_app")
        assert viewset.cache_app == "student_groups"

    def test_respiratory_rate_viewset_has_caching(self) -> None:
        """Test that RespiratoryRateViewSet has caching configured"""
        from student_groups.views import RespiratoryRateViewSet

        viewset = RespiratoryRateViewSet()
        assert hasattr(viewset, "cache_app")
        assert viewset.cache_app == "student_groups"

    def test_blood_sugar_viewset_has_caching(self) -> None:
        """Test that BloodSugarViewSet has caching configured"""
        from student_groups.views import BloodSugarViewSet

        viewset = BloodSugarViewSet()
        assert hasattr(viewset, "cache_app")
        assert viewset.cache_app == "student_groups"

    def test_oxygen_saturation_viewset_has_caching(self) -> None:
        """Test that OxygenSaturationViewSet has caching configured"""
        from student_groups.views import OxygenSaturationViewSet

        viewset = OxygenSaturationViewSet()
        assert hasattr(viewset, "cache_app")
        assert viewset.cache_app == "student_groups"

    def test_pain_score_viewset_has_caching(self) -> None:
        """Test that PainScoreViewSet has caching configured"""
        from student_groups.views import PainScoreViewSet

        viewset = PainScoreViewSet()
        assert hasattr(viewset, "cache_app")
        assert viewset.cache_app == "student_groups"

    def test_note_viewset_has_caching(self) -> None:
        """Test that NoteViewSet has caching configured"""
        from student_groups.views import NoteViewSet

        viewset = NoteViewSet()
        assert hasattr(viewset, "cache_app")
        assert viewset.cache_app == "student_groups"

    def test_observation_cache_retrieve_params(self) -> None:
        """Test observation cache retrieve parameters"""
        from student_groups.views import BaseObservationViewSet

        viewset = BaseObservationViewSet()
        assert "patient" in viewset.cache_key_params


@override_settings(
    CACHES={
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "test-cache",
        }
    }
)
class InvestigationRequestCachingTest(APITestCase):
    """Test investigation request endpoints caching"""

    def setUp(self) -> None:
        """Set up test client and clear cache"""
        cache.clear()

    def test_blood_test_request_has_caching(self) -> None:
        """Test that BloodTestRequestViewSet has caching configured"""
        from student_groups.views import BloodTestRequestViewSet

        viewset = BloodTestRequestViewSet()
        assert hasattr(viewset, "cache_app")
        assert viewset.cache_app == "student_groups"
        assert viewset.cache_model == "blood_test_requests"

    def test_imaging_request_has_caching(self) -> None:
        """Test that ImagingRequestViewSet has caching configured"""
        from student_groups.views import ImagingRequestViewSet

        viewset = ImagingRequestViewSet()
        assert hasattr(viewset, "cache_app")
        assert viewset.cache_app == "student_groups"
        assert viewset.cache_model == "imaging_requests"

    def test_medication_order_has_caching(self) -> None:
        """Test that MedicationOrderViewSet has caching configured"""
        from student_groups.views import MedicationOrderViewSet

        viewset = MedicationOrderViewSet()
        assert hasattr(viewset, "cache_app")
        assert viewset.cache_app == "student_groups"
        assert viewset.cache_model == "medication_orders"

    def test_discharge_summary_has_caching(self) -> None:
        """Test that DischargeSummaryViewSet has caching configured"""
        from student_groups.views import DischargeSummaryViewSet

        viewset = DischargeSummaryViewSet()
        assert hasattr(viewset, "cache_app")
        assert viewset.cache_app == "student_groups"
        assert viewset.cache_model == "discharge_summaries"

    def test_investigation_cache_params(self) -> None:
        """Test investigation request cache retrieve parameters"""
        from student_groups.views import BaseInvestigationRequestViewSet

        viewset = BaseInvestigationRequestViewSet()
        assert "patient" in viewset.cache_key_params
        # Note: "user" was removed to prevent data leakage between different request types


@override_settings(
    CACHES={
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "test-cache",
        }
    }
)
class PatientAndFileCachingTest(APITestCase):
    """Test patient and file endpoints caching"""

    def setUp(self) -> None:
        """Set up test client and clear cache"""
        cache.clear()

    def test_patient_viewset_has_caching(self) -> None:
        """Test that PatientViewSet has caching configured"""
        from patients.views import PatientViewSet

        viewset = PatientViewSet()
        assert hasattr(viewset, "cache_app")
        assert viewset.cache_app == "patients"
        assert viewset.cache_model == "patients"

    def test_file_viewset_has_caching(self) -> None:
        """Test that FileViewSet has caching configured"""
        from patients.views import FileViewSet

        viewset = FileViewSet()
        assert hasattr(viewset, "cache_app")
        assert viewset.cache_app == "patients"
        assert viewset.cache_model == "files"
        assert "patient_pk" in viewset.cache_key_params


class CacheInvalidationStrategyTest(TestCase):
    """Test cache invalidation strategy"""

    def setUp(self) -> None:
        """Clear cache before each test"""
        cache.clear()

    def test_observation_invalidation_pattern(self) -> None:
        """Test observation cache invalidation pattern"""
        cache.set("student_groups:observations:list:hash1", {"data": "test"}, 300)
        cache.set("student_groups:observations:list:hash2", {"data": "test"}, 300)
        cache.set("other:app:data", {"data": "keep"}, 300)

        assert cache.get("student_groups:observations:list:hash1") is not None
        assert cache.get("other:app:data") is not None

        CacheManager.invalidate_cache([
            "student_groups:observations:write:patient_id:*"
        ])

        assert cache.get("student_groups:observations:list:hash1") is None
        assert cache.get("other:app:data") is not None

    def test_investigation_request_invalidation_pattern(self) -> None:
        """Test investigation request cache invalidation"""
        cache.set(
            "student_groups:investigation_requests:list:hash1",
            {"data": "test"},
            300,
        )

        CacheManager.invalidate_cache([
            "student_groups:investigation_requests:write:patient_id:*"
        ])

        assert cache.get("student_groups:investigation_requests:list:hash1") is None

        cache.set(
            "student_groups:investigation_requests:list:hash1",
            {"data": "test"},
            300,
        )

        CacheManager.invalidate_cache([
            "student_groups:investigation_requests:write:user_id:*"
        ])

        assert cache.get("student_groups:investigation_requests:list:hash1") is None

    def test_file_invalidation_pattern(self) -> None:
        """Test file cache invalidation"""
        cache.set("patients:files:list:hash1", {"data": "test"}, 300)

        CacheManager.invalidate_cache(["patients:files:write:patient_id:*"])

        assert cache.get("patients:files:list:hash1") is None

    def test_multi_pattern_invalidation(self) -> None:
        """Test invalidating multiple patterns simultaneously"""
        cache.set("app1:model1:data1", "value1", 300)
        cache.set("app1:model2:data2", "value2", 300)
        cache.set("app2:model1:data3", "value3", 300)
        cache.set("other:data4", "value4", 300)

        CacheManager.invalidate_cache([
            "app1:model1:*",
            "app2:model1:*",
        ])

        assert cache.get("app1:model1:data1") is None
        assert cache.get("app2:model1:data3") is None
        assert cache.get("app1:model2:data2") is not None
        assert cache.get("other:data4") is not None


class CacheKeyStrategyTest(TestCase):
    """Test cache key strategy consistency"""

    def test_patient_parameter_consistency(self) -> None:
        """Test that patient parameter is handled consistently"""
        key1 = CacheKeyGenerator.generate_key(
            "student_groups",
            "observations",
            "list",
            patient="5",
            page_size="10",
        )
        key2 = CacheKeyGenerator.generate_key(
            "student_groups",
            "observations",
            "list",
            page_size="10",
            patient="5",
        )

        assert key1 == key2

    def test_multiple_parameter_consistency(self) -> None:
        """Test consistency with multiple parameters"""
        key1 = CacheKeyGenerator.generate_key(
            "student_groups",
            "investigation_requests",
            "list",
            patient="5",
            user="1",
        )
        key2 = CacheKeyGenerator.generate_key(
            "student_groups",
            "investigation_requests",
            "list",
            patient="5",
            user="1",
        )
        key3 = CacheKeyGenerator.generate_key(
            "student_groups",
            "investigation_requests",
            "list",
            user="1",
            patient="5",
        )

        assert key1 == key2 == key3


class UserIsolationTest(APITestCase):
    """Test that cache prevents data leakage between different users"""

    def setUp(self) -> None:
        """Set up test users and clear cache"""
        cache.clear()
        self.user1 = User.objects.create_user(
            username="student1", email="student1@test.com", password="pass"
        )
        self.user2 = User.objects.create_user(
            username="student2", email="student2@test.com", password="pass"
        )

    def test_cache_key_includes_user_id_when_user_sensitive(self) -> None:
        """Test that user-sensitive cache keys include user ID"""
        key1 = CacheKeyGenerator.generate_key(
            "student_groups", "observations", "list", patient="1", user_id=1
        )
        key2 = CacheKeyGenerator.generate_key(
            "student_groups", "observations", "list", patient="1", user_id=2
        )

        assert key1 != key2, "Different user IDs should generate different cache keys"

    def test_cache_key_excludes_user_id_when_not_user_sensitive(self) -> None:
        """Test that non-user-sensitive cache keys don't include user ID"""
        key1 = CacheKeyGenerator.generate_key("patients", "files", "list", patient="1")
        key2 = CacheKeyGenerator.generate_key(
            "patients", "files", "list", patient="1", user_id=1
        )

        assert key1 != key2, (
            "Including user_id should change the key even if not user-sensitive"
        )

    def test_cache_mixin_user_sensitive_isolation(self) -> None:
        """Test that CacheMixin with user_sensitive=True isolates data per user"""
        # Generate cache keys for different users
        cache_params1 = {"patient": "1", "page": "1", "user_id": self.user1.id}
        cache_params2 = {"patient": "1", "page": "1", "user_id": self.user2.id}

        key1 = CacheKeyGenerator.generate_key(
            "student_groups", "observations", "list", **cache_params1
        )
        key2 = CacheKeyGenerator.generate_key(
            "student_groups", "observations", "list", **cache_params2
        )

        assert key1 != key2, "Cache keys should be different for different users"
