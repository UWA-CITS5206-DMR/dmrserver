from django.test import TestCase, RequestFactory
from django.contrib.auth.models import User, Group
from patients.models import Patient, File
from student_groups.models import LabRequest, ApprovedFile
from core.permissions import (
    get_user_role,
    FileAccessPermission,
    FileManagementPermission,
    PatientPermission,
    ROLE_ADMIN,
    ROLE_INSTRUCTOR,
    ROLE_STUDENT,
)
from django.core.files.uploadedfile import SimpleUploadedFile
from datetime import date
import os


class PermissionTestCase(TestCase):
    def setUp(self):
        # Create groups
        self.admin_group, _ = Group.objects.get_or_create(name="admin")
        self.instructor_group, _ = Group.objects.get_or_create(name="instructor")
        self.student_group, _ = Group.objects.get_or_create(name="student")

        # Create users
        self.admin_user = User.objects.create_user(
            "admin_test", "admin@test.com", "pass"
        )
        self.instructor_user = User.objects.create_user(
            "instructor_test", "instructor@test.com", "pass"
        )
        self.student_user = User.objects.create_user(
            "student_test", "student@test.com", "pass"
        )

        # Assign groups
        self.admin_user.groups.add(self.admin_group)
        self.instructor_user.groups.add(self.instructor_group)
        self.student_user.groups.add(self.student_group)

        # Create test data
        self.patient = Patient.objects.create(
            first_name="Test",
            last_name="Patient",
            date_of_birth="1990-01-01",
            email="test@patient.com",
        )

        # Create a test file
        self.test_file = SimpleUploadedFile(
            "test.pdf", b"test content", content_type="application/pdf"
        )

        self.file = File.objects.create(
            patient=self.patient,
            file=self.test_file,
            display_name="test.pdf",
            requires_pagination=True,
        )

        # Create lab request
        self.lab_request = LabRequest.objects.create(
            patient=self.patient,
            user=self.student_user,
            test_type="blood_test",
            reason="routine check",
            status="completed",
        )

        self.request_factory = RequestFactory()

    def test_get_user_role(self):
        """Test user role detection"""
        self.assertEqual(get_user_role(self.admin_user), ROLE_ADMIN)
        self.assertEqual(get_user_role(self.instructor_user), ROLE_INSTRUCTOR)
        self.assertEqual(get_user_role(self.student_user), ROLE_STUDENT)

        # Test unauthenticated user
        self.assertIsNone(get_user_role(None))

        # Test user without roles
        no_role_user = User.objects.create_user("norole", "norole@test.com", "pass")
        self.assertIsNone(get_user_role(no_role_user))

    def test_file_access_permission_instructor(self):
        """Test instructor can access all files"""
        permission = FileAccessPermission()
        request = self.request_factory.get("/")
        request.user = self.instructor_user

        # Test has_permission
        self.assertTrue(permission.has_permission(request, None))

        # Test has_object_permission
        self.assertTrue(permission.has_object_permission(request, None, self.file))

    def test_file_access_permission_admin(self):
        """Test admin can access all files"""
        permission = FileAccessPermission()
        request = self.request_factory.get("/")
        request.user = self.admin_user

        self.assertTrue(permission.has_permission(request, None))
        self.assertTrue(permission.has_object_permission(request, None, self.file))

    def test_file_access_permission_student_without_approval(self):
        """Test student cannot access file without approval"""
        permission = FileAccessPermission()
        request = self.request_factory.get("/")
        request.user = self.student_user

        # Has basic permission (authenticated)
        self.assertTrue(permission.has_permission(request, None))

        # But no object permission without approval
        self.assertFalse(permission.has_object_permission(request, None, self.file))

    def test_file_access_permission_student_with_approval(self):
        """Test student can access file with approval"""
        # Create approval
        ApprovedFile.objects.create(
            lab_request=self.lab_request, file=self.file, page_range="1-3"
        )

        permission = FileAccessPermission()
        request = self.request_factory.get("/")
        request.user = self.student_user

        self.assertTrue(permission.has_permission(request, None))
        self.assertTrue(permission.has_object_permission(request, None, self.file))

    def test_file_management_permission_instructor(self):
        """Test instructor can manage files"""
        permission = FileManagementPermission()

        # Test GET request
        request = self.request_factory.get("/")
        request.user = self.instructor_user
        self.assertTrue(permission.has_permission(request, None))

        # Test POST request
        request = self.request_factory.post("/")
        request.user = self.instructor_user
        self.assertTrue(permission.has_permission(request, None))

        # Test DELETE request
        request = self.request_factory.delete("/")
        request.user = self.instructor_user
        self.assertTrue(permission.has_permission(request, None))

    def test_file_management_permission_student(self):
        """Test student cannot manage files"""
        permission = FileManagementPermission()

        # Test any request type - should fail for student
        request = self.request_factory.get("/")
        request.user = self.student_user
        self.assertFalse(permission.has_permission(request, None))

        request = self.request_factory.post("/")
        request.user = self.student_user
        self.assertFalse(permission.has_permission(request, None))

    def test_patient_permission_student_read_only(self):
        """Test student has read-only access to patient data"""
        permission = PatientPermission()

        # GET should work
        request = self.request_factory.get("/")
        request.user = self.student_user
        self.assertTrue(permission.has_permission(request, None))

        # POST should fail
        request = self.request_factory.post("/")
        request.user = self.student_user
        self.assertFalse(permission.has_permission(request, None))

        # DELETE should fail
        request = self.request_factory.delete("/")
        request.user = self.student_user
        self.assertFalse(permission.has_permission(request, None))

    def test_patient_permission_instructor_full_access(self):
        """Test instructor has full access to patient data"""
        permission = PatientPermission()

        for method in ["GET", "POST", "PUT", "PATCH", "DELETE"]:
            request = getattr(self.request_factory, method.lower())("/")
            request.user = self.instructor_user
            self.assertTrue(
                permission.has_permission(request, None),
                f"Instructor should have {method} permission",
            )

    def tearDown(self):
        """Clean up test files"""
        if self.file.file:
            try:
                os.remove(self.file.file.path)
            except (OSError, ValueError):
                pass
