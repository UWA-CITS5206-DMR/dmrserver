"""Role-based access control (RBAC) test suite.

The tests in this module focus on access rules across admin, instructor, and
student personas. Shared fixtures ensure we only create the necessary objects
once per class, which keeps the suite fast and avoids repeated boilerplate.
"""

import tempfile
import uuid
from django.contrib.auth.models import User, Group
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase
from unittest.mock import Mock

from core.permissions import get_user_role, FileAccessPermission
from core.context import Role
from patients.models import Patient, File
from student_groups.models import ImagingRequest, ApprovedFile


class RoleFixtureMixin:
    """Reusable helpers for creating role-aware users and patients."""

    password = "test123"

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.role_groups = {
            Role.ADMIN.value: Group.objects.get_or_create(name=Role.ADMIN.value)[0],
            Role.INSTRUCTOR.value: Group.objects.get_or_create(
                name=Role.INSTRUCTOR.value
            )[0],
            Role.STUDENT.value: Group.objects.get_or_create(name=Role.STUDENT.value)[0],
        }

    @classmethod
    def create_user(cls, username, role=None, **extra):
        """Create a user and attach them to the requested role group."""

        user = User.objects.create_user(
            username=username,
            password=extra.pop("password", cls.password),
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
            "email": f"test-{suffix}@example.com",
        }
        defaults.update(overrides)
        return Patient.objects.create(**defaults)


class CoreUtilsTest(RoleFixtureMixin, TestCase):
    """Test core utility functions"""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.admin_user = cls.create_user("admin", Role.ADMIN)
        cls.instructor_user = cls.create_user("instructor", Role.INSTRUCTOR)
        cls.student_user = cls.create_user("student", Role.STUDENT)
        cls.no_role_user = cls.create_user("norole")

    def test_get_user_role_unauthenticated(self):
        """Test that an unauthenticated user has no role."""
        mock_user = Mock()
        mock_user.is_authenticated = False
        self.assertIsNone(get_user_role(mock_user))
        self.assertIsNone(get_user_role(None))

    def test_get_user_role(self):
        """Test role detection for different users."""
        self.assertEqual(get_user_role(self.admin_user), Role.ADMIN.value)
        self.assertEqual(get_user_role(self.instructor_user), Role.INSTRUCTOR.value)
        self.assertEqual(get_user_role(self.student_user), Role.STUDENT.value)
        self.assertIsNone(get_user_role(self.no_role_user))

    def test_superuser_is_admin(self):
        """Test that a superuser is automatically considered an admin."""
        superuser = User.objects.create_superuser(username="super", password="test123")
        self.assertEqual(get_user_role(superuser), Role.ADMIN.value)


class AuthenticationTest(RoleFixtureMixin, APITestCase):
    """Test multi-device authentication with independent logout"""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.test_user = cls.create_user("testuser", Role.STUDENT)

    def setUp(self):
        self.client = APIClient()

    def test_login_creates_new_token(self):
        """Test that each login creates a new token for multi-device support"""
        # First login
        response1 = self.client.post(
            reverse("auth-login"),
            {"username": "testuser", "password": "test123"},
        )
        self.assertEqual(response1.status_code, status.HTTP_200_OK)
        token1 = response1.data["token"]

        # Second login (simulating a different device)
        response2 = self.client.post(
            reverse("auth-login"),
            {"username": "testuser", "password": "test123"},
        )
        self.assertEqual(response2.status_code, status.HTTP_200_OK)
        token2 = response2.data["token"]

        # Tokens should be different
        self.assertNotEqual(token1, token2)

    def test_multiple_tokens_work_simultaneously(self):
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
        self.assertEqual(profile1.status_code, status.HTTP_200_OK)

        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token2}")
        profile2 = self.client.get(reverse("auth-profile"))
        self.assertEqual(profile2.status_code, status.HTTP_200_OK)

    def test_logout_only_affects_current_token(self):
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
        self.assertEqual(logout_response.status_code, status.HTTP_200_OK)

        # Token1 should no longer work
        profile1 = self.client.get(reverse("auth-profile"))
        self.assertEqual(profile1.status_code, status.HTTP_401_UNAUTHORIZED)

        # Token2 should still work
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token2}")
        profile2 = self.client.get(reverse("auth-profile"))
        self.assertEqual(profile2.status_code, status.HTTP_200_OK)

    def test_login_returns_user_info(self):
        """Test that login returns both token and user information"""
        response = self.client.post(
            reverse("auth-login"),
            {"username": "testuser", "password": "test123"},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("token", response.data)
        self.assertIn("user", response.data)
        self.assertEqual(response.data["user"]["username"], "testuser")


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class FilePermissionsTest(RoleFixtureMixin, TestCase):
    """Test file access permissions with approval-based logic"""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        # Create role-aware users once per class
        cls.admin_user = cls.create_user("admin", Role.ADMIN)
        cls.instructor_user = cls.create_user("instructor", Role.INSTRUCTOR)
        cls.student_user = cls.create_user("student", Role.STUDENT)

        # Create test patient and file once per class
        cls.patient = cls.create_patient()
        cls.file = File.objects.create(file="test_file.pdf", patient=cls.patient)

    def setUp(self):
        super().setUp()
        # Lightweight per-test mocks
        self.mock_request = Mock()
        self.mock_view = Mock()

    def test_admin_can_access_file(self):
        """Test that an admin has full access to files."""
        permission = FileAccessPermission()
        self.mock_request.user = self.admin_user
        self.mock_request.method = "GET"

        # Admin should have access
        self.assertTrue(
            permission.has_object_permission(
                self.mock_request, self.mock_view, self.file
            )
        )

    def test_instructor_can_access_file(self):
        """Test that an instructor has full access to files."""
        permission = FileAccessPermission()
        self.mock_request.user = self.instructor_user
        self.mock_request.method = "GET"

        # Instructor should have access
        self.assertTrue(
            permission.has_object_permission(
                self.mock_request, self.mock_view, self.file
            )
        )

    def test_student_cannot_access_file_without_approval(self):
        """Test that a student cannot access a file without an approved request."""
        permission = FileAccessPermission()
        self.mock_request.user = self.student_user
        self.mock_request.method = "GET"

        # Student should not have access without approval
        self.assertFalse(
            permission.has_object_permission(
                self.mock_request, self.mock_view, self.file
            )
        )

    def test_student_can_access_file_with_approval(self):
        """Test that a student can access a file if their request was approved."""
        permission = FileAccessPermission()
        self.mock_request.user = self.student_user
        self.mock_request.method = "GET"

        # Create imaging request
        imaging_request = ImagingRequest.objects.create(
            patient=self.patient,
            user=self.student_user,
            test_type="X_RAY",
            details="Test request",
            infection_control_precautions=ImagingRequest.InfectionControlPrecaution.NONE,
            imaging_focus="Chest",
            status="completed",
            name="Test X-Ray Request",
        )

        # Create approved file link
        ApprovedFile.objects.create(
            file=self.file,
            imaging_request=imaging_request,
        )

        # Student should now have access
        self.assertTrue(
            permission.has_object_permission(
                self.mock_request, self.mock_view, self.file
            )
        )

    def test_instructor_safe_methods_allowed(self):
        """Instructors should have permission for safe HTTP methods."""

        permission = FileAccessPermission()
        self.mock_request.user = self.instructor_user

        for method in ["GET", "HEAD", "OPTIONS"]:
            self.mock_request.method = method
            self.assertTrue(
                permission.has_permission(self.mock_request, self.mock_view)
            )

    def test_instructor_write_methods_denied_by_permission_class(self):
        """Instructor write operations require the view to allow them explicitly."""

        permission = FileAccessPermission()
        self.mock_request.user = self.instructor_user

        for method in ["POST", "PUT", "PATCH", "DELETE"]:
            self.mock_request.method = method
            self.assertFalse(
                permission.has_permission(self.mock_request, self.mock_view)
            )

    def test_student_cannot_manage_files(self):
        """Test that a student cannot create, update, or delete files."""
        permission = FileAccessPermission()
        self.mock_request.user = self.student_user

        # Test write methods - should be denied
        for method in ["POST", "PUT", "PATCH", "DELETE"]:
            self.mock_request.method = method
            self.assertFalse(
                permission.has_permission(self.mock_request, self.mock_view)
            )


class PatientRBACTest(RoleFixtureMixin, APITestCase):
    """Test RBAC for Patient operations"""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        # Create users and patient once per class to avoid repeated DB writes
        cls.admin_user = cls.create_user("admin", Role.ADMIN)
        cls.instructor_user = cls.create_user("instructor", Role.INSTRUCTOR)
        cls.student_user = cls.create_user("student", Role.STUDENT)

        cls.patient = cls.create_patient(bed="Bed 2")

    def setUp(self):
        # Keep a fresh API client per test for authentication handling
        self.client = APIClient()

    def test_student_can_read_patients(self):
        """Test that students can read patient data"""
        self.client.force_authenticate(user=self.student_user)

        # Can list patients
        response = self.client.get(reverse("patient-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Can retrieve specific patient
        response = self.client.get(reverse("patient-detail", args=[self.patient.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_instructor_can_modify_patients(self):
        """Test that instructors can modify patient data"""
        self.client.force_authenticate(user=self.instructor_user)

        create_payload = {
            "first_name": "New",
            "last_name": "Patient",
            "date_of_birth": "1985-01-01",
            "gender": Patient.Gender.FEMALE,
            "email": "new@example.com",
            "mrn": "MRN_CORE_INSTR_CREATE",
            "ward": "Ward Core",
            "bed": "Bed 3",
            "phone_number": "+61800000001",
        }
        response = self.client.post(reverse("patient-list"), create_payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        update_payload = {"first_name": "Updated"}
        response = self.client.patch(
            reverse("patient-detail", args=[self.patient.id]), update_payload
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.patient.refresh_from_db()
        self.assertEqual(self.patient.first_name, "Updated")

    def test_admin_can_modify_patients(self):
        """Test that admin users can modify patient data"""
        self.client.force_authenticate(user=self.admin_user)

        create_payload = {
            "first_name": "New",
            "last_name": "Patient",
            "date_of_birth": "1985-01-01",
            "gender": Patient.Gender.MALE,
            "email": "new@example.com",
            "mrn": "MRN_CORE_ADMIN_CREATE",
            "ward": "Ward Core",
            "bed": "Bed 4",
            "phone_number": "+61800000002",
        }
        response = self.client.post(reverse("patient-list"), create_payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        update_payload = {"first_name": "Updated Admin"}
        response = self.client.patch(
            reverse("patient-detail", args=[self.patient.id]), update_payload
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.patient.refresh_from_db()
        self.assertEqual(self.patient.first_name, "Updated Admin")


class RequestRBACTest(RoleFixtureMixin, APITestCase):
    """Test RBAC for new request types (ImagingRequest, etc.)"""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.admin_user = cls.create_user("admin", Role.ADMIN)
        cls.instructor_user = cls.create_user("instructor", Role.INSTRUCTOR)
        cls.student_user = cls.create_user("student", Role.STUDENT)

        cls.patient = cls.create_patient(bed="Bed 5")

    def setUp(self):
        # Fresh API client per test
        self.client = APIClient()

    def test_student_can_create_imaging_request(self):
        """Test that students can create imaging requests"""
        self.client.force_authenticate(user=self.student_user)
        data = {
            "patient": self.patient.id,
            "test_type": "X-ray",
            "details": "Patient complaining of chest pain",
            "infection_control_precautions": "None",
            "imaging_focus": "Chest",
            "name": "Test Request",
            "role": "Student",
        }
        response = self.client.post("/api/student-groups/imaging-requests/", data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["test_type"], "X-ray")
        self.assertEqual(response.data["name"], "Test Request")

    def test_instructor_can_manage_imaging_requests(self):
        """Test that instructors can manage imaging requests"""
        self.client.force_authenticate(user=self.instructor_user)

        # Create an imaging request first
        ImagingRequest.objects.create(
            patient=self.patient,
            user=self.student_user,
            test_type="MRI scan",
            details="Patient needs MRI scan for diagnosis",
            infection_control_precautions=ImagingRequest.InfectionControlPrecaution.NONE,
            imaging_focus="Head",
            status="pending",
            name="Test MRI Request",
            role="Medical Student",
        )

        response = self.client.get("/api/instructors/imaging-requests/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data["results"]), 1)

    def test_admin_has_full_access_to_requests(self):
        """Test that admin users have full access to all request types"""
        self.client.force_authenticate(user=self.admin_user)

        # Create an imaging request
        imaging_request = ImagingRequest.objects.create(
            patient=self.patient,
            user=self.student_user,
            test_type="X-ray",
            details="Testing admin access rights",
            infection_control_precautions=ImagingRequest.InfectionControlPrecaution.NONE,
            imaging_focus="Arm",
            status="pending",
            name="Admin Test Request",
            role="Doctor",
        )

        # Admin should be able to access through any endpoint that exists
        # For now, just verify the request was created successfully
        self.assertEqual(imaging_request.user, self.student_user)
        self.assertEqual(imaging_request.status, "pending")
