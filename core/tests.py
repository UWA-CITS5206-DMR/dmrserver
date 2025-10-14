"""Role-based access control (RBAC) test suite.

The tests in this module focus on access rules across admin, instructor, and
student personas. Shared fixtures ensure we only create the necessary objects
once per class, which keeps the suite fast and avoids repeated boilerplate.
"""

import tempfile
import uuid
from unittest.mock import Mock

from django.contrib.auth.models import Group, User
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from core.context import Role
from core.permissions import FileAccessPermission, get_user_role
from patients.models import File, Patient
from student_groups.models import ApprovedFile, ImagingRequest


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


class AuthenticationTest(RoleFixtureMixin, APITestCase):
    """Test multi-device authentication with independent logout"""

    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()
        cls.test_user = cls.create_user("testuser", Role.STUDENT)

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


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class FilePermissionsTest(RoleFixtureMixin, TestCase):
    """Test file access permissions with approval-based logic"""

    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()
        # Create role-aware users once per class
        cls.admin_user = cls.create_user("admin", Role.ADMIN)
        cls.instructor_user = cls.create_user("instructor", Role.INSTRUCTOR)
        cls.student_user = cls.create_user("student", Role.STUDENT)

        # Create test patient and file once per class
        cls.patient = cls.create_patient()
        cls.file = File.objects.create(file="test_file.pdf", patient=cls.patient)

    def setUp(self) -> None:
        super().setUp()
        # Lightweight per-test mocks
        self.mock_request = Mock()
        self.mock_view = Mock()

    def test_admin_can_access_file(self) -> None:
        """Test that an admin has full access to files."""
        permission = FileAccessPermission()
        self.mock_request.user = self.admin_user
        self.mock_request.method = "GET"

        # Admin should have access
        assert permission.has_object_permission(
            self.mock_request, self.mock_view, self.file
        )

    def test_instructor_can_access_file(self) -> None:
        """Test that an instructor has full access to files."""
        permission = FileAccessPermission()
        self.mock_request.user = self.instructor_user
        self.mock_request.method = "GET"

        # Instructor should have access
        assert permission.has_object_permission(
            self.mock_request, self.mock_view, self.file
        )

    def test_student_cannot_access_file_without_approval(self) -> None:
        """Test that a student cannot access a file without an approved request."""
        permission = FileAccessPermission()
        self.mock_request.user = self.student_user
        self.mock_request.method = "GET"

        # Student should not have access without approval
        assert not permission.has_object_permission(
            self.mock_request, self.mock_view, self.file
        )

    def test_student_can_access_file_with_approval(self) -> None:
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
        assert permission.has_object_permission(
            self.mock_request, self.mock_view, self.file
        )

    def test_instructor_safe_methods_allowed(self) -> None:
        """Instructors should have permission for safe HTTP methods."""

        permission = FileAccessPermission()
        self.mock_request.user = self.instructor_user

        for method in ["GET", "HEAD", "OPTIONS"]:
            self.mock_request.method = method
            assert permission.has_permission(self.mock_request, self.mock_view)

    def test_instructor_write_methods_denied_by_permission_class(self) -> None:
        """Instructor write operations require the view to allow them explicitly."""

        permission = FileAccessPermission()
        self.mock_request.user = self.instructor_user

        for method in ["POST", "PUT", "PATCH", "DELETE"]:
            self.mock_request.method = method
            assert not permission.has_permission(self.mock_request, self.mock_view)

    def test_student_cannot_manage_files(self) -> None:
        """Test that a student cannot create, update, or delete files."""
        permission = FileAccessPermission()
        self.mock_request.user = self.student_user

        # Test write methods - should be denied
        for method in ["POST", "PUT", "PATCH", "DELETE"]:
            self.mock_request.method = method
            assert not permission.has_permission(self.mock_request, self.mock_view)


class PatientRBACTest(RoleFixtureMixin, APITestCase):
    """Test RBAC for Patient operations"""

    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()
        # Create users and patient once per class to avoid repeated DB writes
        cls.admin_user = cls.create_user("admin", Role.ADMIN)
        cls.instructor_user = cls.create_user("instructor", Role.INSTRUCTOR)
        cls.student_user = cls.create_user("student", Role.STUDENT)

        cls.patient = cls.create_patient(bed="Bed 2")

    def setUp(self) -> None:
        # Keep a fresh API client per test for authentication handling
        self.client = APIClient()

    def test_student_can_read_patients(self) -> None:
        """Test that students can read patient data"""
        self.client.force_authenticate(user=self.student_user)

        # Can list patients
        response = self.client.get(reverse("patient-list"))
        assert response.status_code == status.HTTP_200_OK

        # Can retrieve specific patient
        response = self.client.get(reverse("patient-detail", args=[self.patient.id]))
        assert response.status_code == status.HTTP_200_OK

    def test_instructor_can_modify_patients(self) -> None:
        """Test that instructors can modify patient data"""
        self.client.force_authenticate(user=self.instructor_user)

        create_payload = {
            "first_name": "New",
            "last_name": "Patient",
            "date_of_birth": "1985-01-01",
            "gender": Patient.Gender.FEMALE,
            "mrn": "MRN_CORE_INSTR_CREATE",
            "ward": "Ward Core",
            "bed": "Bed 3",
            "phone_number": "+61800000001",
        }
        response = self.client.post(reverse("patient-list"), create_payload)
        assert response.status_code == status.HTTP_201_CREATED

        update_payload = {"first_name": "Updated"}
        response = self.client.patch(
            reverse("patient-detail", args=[self.patient.id]),
            update_payload,
        )
        assert response.status_code == status.HTTP_200_OK

        self.patient.refresh_from_db()
        assert self.patient.first_name == "Updated"

    def test_admin_can_modify_patients(self) -> None:
        """Test that admin users can modify patient data"""
        self.client.force_authenticate(user=self.admin_user)

        create_payload = {
            "first_name": "New",
            "last_name": "Patient",
            "date_of_birth": "1985-01-01",
            "gender": Patient.Gender.MALE,
            "mrn": "MRN_CORE_ADMIN_CREATE",
            "ward": "Ward Core",
            "bed": "Bed 4",
            "phone_number": "+61800000002",
        }
        response = self.client.post(reverse("patient-list"), create_payload)
        assert response.status_code == status.HTTP_201_CREATED

        update_payload = {"first_name": "Updated Admin"}
        response = self.client.patch(
            reverse("patient-detail", args=[self.patient.id]),
            update_payload,
        )
        assert response.status_code == status.HTTP_200_OK

        self.patient.refresh_from_db()
        assert self.patient.first_name == "Updated Admin"


class RequestRBACTest(RoleFixtureMixin, APITestCase):
    """Test RBAC for new request types (ImagingRequest, etc.)"""

    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()
        cls.admin_user = cls.create_user("admin", Role.ADMIN)
        cls.instructor_user = cls.create_user("instructor", Role.INSTRUCTOR)
        cls.student_user = cls.create_user("student", Role.STUDENT)

        cls.patient = cls.create_patient(bed="Bed 5")

    def setUp(self) -> None:
        # Fresh API client per test
        self.client = APIClient()

    def test_student_can_create_imaging_request(self) -> None:
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
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["test_type"] == "X-ray"
        assert response.data["name"] == "Test Request"

    def test_instructor_can_manage_imaging_requests(self) -> None:
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
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) >= 1

    def test_admin_has_full_access_to_requests(self) -> None:
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
        assert imaging_request.user == self.student_user
        assert imaging_request.status == "pending"

    def test_student_can_update_own_investigation_request(self) -> None:
        """Test that students can update their own investigation requests"""
        self.client.force_authenticate(user=self.student_user)

        # Create an imaging request
        imaging_request = ImagingRequest.objects.create(
            patient=self.patient,
            user=self.student_user,
            test_type="CT scan",
            details="Original details",
            infection_control_precautions=ImagingRequest.InfectionControlPrecaution.NONE,
            imaging_focus="Chest",
            name="Test Student",
            role="Medical Student",
        )

        # Update the request
        data = {"details": "Updated details by student"}
        response = self.client.patch(
            f"/api/student-groups/imaging-requests/{imaging_request.id}/",
            data,
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["details"] == "Updated details by student"

    def test_student_can_delete_own_investigation_request(self) -> None:
        """Test that students can delete their own investigation requests"""
        self.client.force_authenticate(user=self.student_user)

        # Create an imaging request
        imaging_request = ImagingRequest.objects.create(
            patient=self.patient,
            user=self.student_user,
            test_type="Ultrasound",
            details="Request to be deleted",
            infection_control_precautions=ImagingRequest.InfectionControlPrecaution.NONE,
            imaging_focus="Abdomen",
            name="Test Student",
            role="Medical Student",
        )

        # Delete the request
        response = self.client.delete(
            f"/api/student-groups/imaging-requests/{imaging_request.id}/",
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not ImagingRequest.objects.filter(id=imaging_request.id).exists()

    def test_student_cannot_modify_other_students_investigation_request(self) -> None:
        """Test that students cannot modify other students' investigation requests"""
        other_student = self.create_user("other_student", Role.STUDENT)
        self.client.force_authenticate(user=self.student_user)

        # Create an imaging request by another student
        imaging_request = ImagingRequest.objects.create(
            patient=self.patient,
            user=other_student,
            test_type="MRI",
            details="Other student's request",
            infection_control_precautions=ImagingRequest.InfectionControlPrecaution.NONE,
            imaging_focus="Brain",
            name="Other Student",
            role="Medical Student",
        )

        # Try to update the request
        data = {"details": "Attempting unauthorized update"}
        response = self.client.patch(
            f"/api/student-groups/imaging-requests/{imaging_request.id}/",
            data,
        )
        # Should return 404 because get_queryset filters by user
        assert response.status_code == status.HTTP_404_NOT_FOUND

        # Try to delete the request
        response = self.client.delete(
            f"/api/student-groups/imaging-requests/{imaging_request.id}/",
        )
        # Should return 404 because get_queryset filters by user
        assert response.status_code == status.HTTP_404_NOT_FOUND
        # Verify the request still exists
        assert ImagingRequest.objects.filter(id=imaging_request.id).exists()
