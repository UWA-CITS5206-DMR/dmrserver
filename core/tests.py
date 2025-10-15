"""Role-based access control (RBAC) test suite.

The tests in this module focus on access rules across admin, instructor, and
student personas. Shared fixtures ensure we only create the necessary objects
once per class, which keeps the suite fast and avoids repeated boilerplate.
"""

import uuid
from unittest.mock import Mock

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


class MedicationOrderPermissionTest(RoleFixtureMixin, TestCase):
    """Test MedicationOrderPermission access rules."""

    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()
        cls.student = cls.create_user("student_perm", Role.STUDENT)
        cls.instructor = cls.create_user("instructor_perm", Role.INSTRUCTOR)
        cls.admin = cls.create_user("admin_perm", Role.ADMIN)

        # Create a mock medication order object
        cls.medication_order = Mock()
        cls.medication_order.user = cls.student

        # Create another medication order for different user
        cls.other_medication_order = Mock()
        cls.other_medication_order.user = cls.create_user("other_student", Role.STUDENT)

    def setUp(self) -> None:
        self.permission = MedicationOrderPermission()

    def test_student_can_read_own_medication_order(self) -> None:
        """Students can read their own medication orders."""
        request = Mock()
        request.user = self.student
        request.method = "GET"

        assert self.permission.has_permission(request, None)
        assert self.permission.has_object_permission(
            request, None, self.medication_order
        )

    def test_student_can_create_medication_order(self) -> None:
        """Students can create medication orders."""
        request = Mock()
        request.user = self.student
        request.method = "POST"

        assert self.permission.has_permission(request, None)

    def test_student_can_update_own_medication_order(self) -> None:
        """Students can update their own medication orders."""
        request = Mock()
        request.user = self.student
        request.method = "PUT"

        assert self.permission.has_permission(request, None)
        assert self.permission.has_object_permission(
            request, None, self.medication_order
        )

    def test_student_can_patch_own_medication_order(self) -> None:
        """Students can patch their own medication orders."""
        request = Mock()
        request.user = self.student
        request.method = "PATCH"

        assert self.permission.has_permission(request, None)
        assert self.permission.has_object_permission(
            request, None, self.medication_order
        )

    def test_student_can_delete_own_medication_order(self) -> None:
        """Students can delete their own medication orders."""
        request = Mock()
        request.user = self.student
        request.method = "DELETE"

        assert self.permission.has_permission(request, None)
        assert self.permission.has_object_permission(
            request, None, self.medication_order
        )

    def test_student_cannot_access_other_medication_order(self) -> None:
        """Students cannot access other students' medication orders."""
        request = Mock()
        request.user = self.student
        request.method = "GET"

        assert not self.permission.has_object_permission(
            request, None, self.other_medication_order
        )

    def test_instructor_has_full_access(self) -> None:
        """Instructors have full access to all medication orders."""
        request = Mock()
        request.user = self.instructor
        request.method = "PUT"

        assert self.permission.has_permission(request, None)
        assert self.permission.has_object_permission(
            request, None, self.medication_order
        )
        assert self.permission.has_object_permission(
            request, None, self.other_medication_order
        )

    def test_admin_has_full_access(self) -> None:
        """Admins have full access to all medication orders."""
        request = Mock()
        request.user = self.admin
        request.method = "DELETE"

        assert self.permission.has_permission(request, None)
        assert self.permission.has_object_permission(
            request, None, self.medication_order
        )

    def test_unauthenticated_user_denied(self) -> None:
        """Unauthenticated users are denied access."""
        request = Mock()
        request.user = Mock()
        request.user.is_authenticated = False
        request.method = "GET"

        assert not self.permission.has_permission(request, None)
        assert not self.permission.has_object_permission(
            request, None, self.medication_order
        )


class DischargeSummaryPermissionTest(RoleFixtureMixin, TestCase):
    """Test DischargeSummaryPermission access rules."""

    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()
        cls.student = cls.create_user("student_ds_perm", Role.STUDENT)
        cls.instructor = cls.create_user("instructor_ds_perm", Role.INSTRUCTOR)
        cls.admin = cls.create_user("admin_ds_perm", Role.ADMIN)

        # Create a mock discharge summary object
        cls.discharge_summary = Mock()
        cls.discharge_summary.user = cls.student

        # Create another discharge summary for different user
        cls.other_discharge_summary = Mock()
        cls.other_discharge_summary.user = cls.create_user(
            "other_student_ds", Role.STUDENT
        )

    def setUp(self) -> None:
        self.permission = DischargeSummaryPermission()

    def test_student_can_read_own_discharge_summary(self) -> None:
        """Students can read their own discharge summaries."""
        request = Mock()
        request.user = self.student
        request.method = "GET"

        assert self.permission.has_permission(request, None)
        assert self.permission.has_object_permission(
            request, None, self.discharge_summary
        )

    def test_student_can_create_discharge_summary(self) -> None:
        """Students can create discharge summaries."""
        request = Mock()
        request.user = self.student
        request.method = "POST"

        assert self.permission.has_permission(request, None)

    def test_student_can_update_own_discharge_summary(self) -> None:
        """Students can update their own discharge summaries."""
        request = Mock()
        request.user = self.student
        request.method = "PUT"

        assert self.permission.has_permission(request, None)
        assert self.permission.has_object_permission(
            request, None, self.discharge_summary
        )

    def test_student_can_patch_own_discharge_summary(self) -> None:
        """Students can patch their own discharge summaries."""
        request = Mock()
        request.user = self.student
        request.method = "PATCH"

        assert self.permission.has_permission(request, None)
        assert self.permission.has_object_permission(
            request, None, self.discharge_summary
        )

    def test_student_can_delete_own_discharge_summary(self) -> None:
        """Students can delete their own discharge summaries."""
        request = Mock()
        request.user = self.student
        request.method = "DELETE"

        assert self.permission.has_permission(request, None)
        assert self.permission.has_object_permission(
            request, None, self.discharge_summary
        )

    def test_student_cannot_access_other_discharge_summary(self) -> None:
        """Students cannot access other students' discharge summaries."""
        request = Mock()
        request.user = self.student
        request.method = "GET"

        assert not self.permission.has_object_permission(
            request, None, self.other_discharge_summary
        )

    def test_instructor_has_full_access(self) -> None:
        """Instructors have full access to all discharge summaries."""
        request = Mock()
        request.user = self.instructor
        request.method = "PUT"

        assert self.permission.has_permission(request, None)
        assert self.permission.has_object_permission(
            request, None, self.discharge_summary
        )
        assert self.permission.has_object_permission(
            request, None, self.other_discharge_summary
        )

    def test_admin_has_full_access(self) -> None:
        """Admins have full access to all discharge summaries."""
        request = Mock()
        request.user = self.admin
        request.method = "DELETE"

        assert self.permission.has_permission(request, None)
        assert self.permission.has_object_permission(
            request, None, self.discharge_summary
        )

    def test_unauthenticated_user_denied(self) -> None:
        """Unauthenticated users are denied access."""
        request = Mock()
        request.user = Mock()
        request.user.is_authenticated = False
        request.method = "GET"

        assert not self.permission.has_permission(request, None)
        assert not self.permission.has_object_permission(
            request, None, self.discharge_summary
        )
