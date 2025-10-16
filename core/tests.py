"""Role-based access control (RBAC) test suite.

The tests in this module focus on access rules across admin, instructor, and
student personas. Shared fixtures ensure we only create the necessary objects
once per class, which keeps the suite fast and avoids repeated boilerplate.
"""

import uuid
from unittest.mock import Mock, patch

from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from core.context import Role
from core.permissions import (
    DischargeSummaryPermission,
    MedicationOrderPermission,
    get_user_role,
)
from patients.models import Patient


class RoleFixtureMixin:
    """Reusable helpers for creating role-aware users and patients."""

    # Intentionally using a fixed test password for fixtures. Marked to ignore S105.
    DEFAULT_PASSWORD = "test123"  # noqa: S105

    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()
        cls.role_groups = {
            Role.ADMIN.value: Group.objects.get_or_create(name=Role.ADMIN.value)[0],
            Role.INSTRUCTOR.value: Group.objects.get_or_create(
                name=Role.INSTRUCTOR.value,
            )[0],
            Role.STUDENT.value: Group.objects.get_or_create(name=Role.STUDENT.value)[0],
        }

    @classmethod
    def create_user(cls, username, role=None, **extra):
        """Create a user and attach them to the requested role group."""

        user = User.objects.create_user(
            username=username,
            password=extra.pop("password", cls.DEFAULT_PASSWORD),
            **extra,
        )
        if role:
            role_value = role.value if isinstance(role, Role) else role
            user.groups.add(cls.role_groups[role_value])
        return user

    @classmethod
    def create_patient(cls, **overrides):
        """Create a patient with the new mandatory identifiers populated."""

        suffix = uuid.uuid4().hex[:8]
        defaults = {
            "first_name": "Test",
            "last_name": "Patient",
            "date_of_birth": "1990-01-01",
            "gender": Patient.Gender.UNSPECIFIED,
            "mrn": f"MRN_CORE_{suffix}",
            "ward": "Ward Core",
            "bed": "Bed 1",
            "phone_number": f"+7000{suffix[:6]}",
        }
        defaults.update(overrides)
        return Patient.objects.create(**defaults)


class CoreUtilsTest(RoleFixtureMixin, TestCase):
    """Test core utility functions"""

    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()
        cls.admin_user = cls.create_user("admin", Role.ADMIN)
        cls.instructor_user = cls.create_user("instructor", Role.INSTRUCTOR)
        cls.student_user = cls.create_user("student", Role.STUDENT)
        cls.no_role_user = cls.create_user("norole")

    def test_get_user_role_unauthenticated(self) -> None:
        """Test that an unauthenticated user has no role."""
        mock_user = Mock()
        mock_user.is_authenticated = False
        assert get_user_role(mock_user) is None
        assert get_user_role(None) is None

    def test_get_user_role(self) -> None:
        """Test role detection for different users."""
        assert get_user_role(self.admin_user) == Role.ADMIN.value
        assert get_user_role(self.instructor_user) == Role.INSTRUCTOR.value
        assert get_user_role(self.student_user) == Role.STUDENT.value
        assert get_user_role(self.no_role_user) is None

    def test_superuser_is_admin(self) -> None:
        """Test that a superuser is automatically considered an admin."""
        superuser = User.objects.create_superuser(username="super", password="test123")
        assert get_user_role(superuser) == Role.ADMIN.value


class AuthenticationTest(APITestCase):
    """Test multi-device authentication with independent logout"""

    @classmethod
    def setUpTestData(cls) -> None:
        cls.test_user = User.objects.create_user(
            username="testuser", password="test123"
        )
        student_group = Group.objects.get_or_create(name=Role.STUDENT.value)[0]
        cls.test_user.groups.add(student_group)

    def setUp(self) -> None:
        self.client = APIClient()

    def test_login_creates_new_token(self) -> None:
        """Test that each login creates a new token for multi-device support"""
        # First login
        response1 = self.client.post(
            reverse("auth-login"),
            {"username": "testuser", "password": "test123"},
        )
        assert response1.status_code == status.HTTP_200_OK
        token1 = response1.data["token"]

        # Second login (simulating a different device)
        response2 = self.client.post(
            reverse("auth-login"),
            {"username": "testuser", "password": "test123"},
        )
        assert response2.status_code == status.HTTP_200_OK
        token2 = response2.data["token"]

        # Tokens should be different
        assert token1 != token2

    def test_multiple_tokens_work_simultaneously(self) -> None:
        """Test that multiple tokens for the same user can be used simultaneously"""
        # Login from device 1
        response1 = self.client.post(
            reverse("auth-login"),
            {"username": "testuser", "password": "test123"},
        )
        token1 = response1.data["token"]

        # Login from device 2
        response2 = self.client.post(
            reverse("auth-login"),
            {"username": "testuser", "password": "test123"},
        )
        token2 = response2.data["token"]

        # Both tokens should work
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token1}")
        profile1 = self.client.get(reverse("auth-profile"))
        assert profile1.status_code == status.HTTP_200_OK

        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token2}")
        profile2 = self.client.get(reverse("auth-profile"))
        assert profile2.status_code == status.HTTP_200_OK

    def test_logout_only_affects_current_token(self) -> None:
        """Test that logging out from one device doesn't affect other devices"""
        # Login from device 1
        response1 = self.client.post(
            reverse("auth-login"),
            {"username": "testuser", "password": "test123"},
        )
        token1 = response1.data["token"]

        # Login from device 2
        response2 = self.client.post(
            reverse("auth-login"),
            {"username": "testuser", "password": "test123"},
        )
        token2 = response2.data["token"]

        # Logout from device 1
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token1}")
        logout_response = self.client.post(reverse("auth-logout"))
        assert logout_response.status_code == status.HTTP_200_OK

        # Token1 should no longer work
        profile1 = self.client.get(reverse("auth-profile"))
        assert profile1.status_code == status.HTTP_401_UNAUTHORIZED

        # Token2 should still work
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token2}")
        profile2 = self.client.get(reverse("auth-profile"))
        assert profile2.status_code == status.HTTP_200_OK

    def test_login_returns_user_info(self) -> None:
        """Test that login returns both token and user information"""
        response = self.client.post(
            reverse("auth-login"),
            {"username": "testuser", "password": "test123"},
        )
        assert response.status_code == status.HTTP_200_OK
        assert "token" in response.data
        assert "user" in response.data
        assert response.data["user"]["username"] == "testuser"


class _BasePermissionBehaviorTest(RoleFixtureMixin, TestCase):
    """Shared behaviour checks for role-aware permissions."""

    permission_class = MedicationOrderPermission

    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()
        cls.student = cls.create_user(
            f"student_{cls.permission_class.__name__.lower()}",
            Role.STUDENT,
        )
        cls.other_student = cls.create_user(
            f"other_student_{cls.permission_class.__name__.lower()}",
            Role.STUDENT,
        )
        cls.instructor = cls.create_user(
            f"instructor_{cls.permission_class.__name__.lower()}",
            Role.INSTRUCTOR,
        )
        cls.admin = cls.create_user(
            f"admin_{cls.permission_class.__name__.lower()}",
            Role.ADMIN,
        )

    def setUp(self) -> None:
        self.permission = self.permission_class()
        self.owned_obj = Mock()
        self.owned_obj.user = self.student
        self.other_obj = Mock()
        self.other_obj.user = self.other_student

    def _build_request(self, user, method: str):
        request = Mock()
        request.user = user
        request.method = method
        return request

    def test_student_access_requires_ownership(self) -> None:
        """Students keep method access but are blocked on foreign objects."""

        for method in ("GET", "POST", "PUT", "PATCH", "DELETE"):
            with self.subTest(method=method):
                request = self._build_request(self.student, method)
                assert self.permission.has_permission(request, None)
                assert self.permission.has_object_permission(
                    request,
                    None,
                    self.owned_obj,
                )

                assert not self.permission.has_object_permission(
                    request,
                    None,
                    self.other_obj,
                )

    def test_student_denied_when_object_missing_user(self) -> None:
        """Objects without ownership metadata must be rejected for students."""

        anonymous_obj = Mock()
        delattr(anonymous_obj, "user")
        request = self._build_request(self.student, "GET")

        assert not self.permission.has_object_permission(
            request,
            None,
            anonymous_obj,
        )

    def test_instructor_has_full_access(self) -> None:
        request = self._build_request(self.instructor, "DELETE")

        assert self.permission.has_permission(request, None)
        assert self.permission.has_object_permission(request, None, self.owned_obj)
        assert self.permission.has_object_permission(request, None, self.other_obj)

    def test_admin_has_full_access(self) -> None:
        request = self._build_request(self.admin, "PATCH")

        assert self.permission.has_permission(request, None)
        assert self.permission.has_object_permission(request, None, self.owned_obj)

    def test_unauthenticated_user_denied(self) -> None:
        unauthenticated = Mock()
        unauthenticated.is_authenticated = False
        request = self._build_request(unauthenticated, "GET")

        assert not self.permission.has_permission(request, None)
        assert not self.permission.has_object_permission(
            request,
            None,
            self.owned_obj,
        )

    def test_role_lookup_cached_after_first_access(self) -> None:
        """BaseRolePermission should memoise role lookups per username."""

        request = self._build_request(self.student, "GET")

        with patch(
            "core.permissions.get_user_role", return_value=Role.STUDENT.value
        ) as mocked_role:
            assert self.permission.has_permission(request, None)
            assert self.permission.has_permission(request, None)

        # Two permission checks should only trigger one expensive role lookup.
        assert mocked_role.call_count == 1


class MedicationOrderPermissionTest(_BasePermissionBehaviorTest):
    permission_class = MedicationOrderPermission


class DischargeSummaryPermissionTest(_BasePermissionBehaviorTest):
    permission_class = DischargeSummaryPermission
