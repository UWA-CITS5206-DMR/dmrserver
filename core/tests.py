"""
Tests for role-based access control (RBAC) system.

This module tests the permission system for different user roles:
- admin: Full access to all resources
- instructor: Full CRUD access to patients and lab requests
- student: Can create lab requests, read-only access to patient data
"""

from django.contrib.auth.models import User, Group
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from core.permissions import get_user_role, ROLE_ADMIN, ROLE_INSTRUCTOR, ROLE_STUDENT
from patients.models import Patient
from student_groups.models import LabRequest


class RolePermissionTest(TestCase):
    """Test the role detection and permission logic"""

    def setUp(self):
        # Create user groups
        self.admin_group = Group.objects.get(name="admin")
        self.instructor_group = Group.objects.get(name="instructor")
        self.student_group = Group.objects.get(name="student")

        # Create test users
        self.admin_user = User.objects.create_user(username="admin", password="test123")
        self.instructor_user = User.objects.create_user(
            username="instructor", password="test123"
        )
        self.student_user = User.objects.create_user(
            username="student", password="test123"
        )
        self.no_role_user = User.objects.create_user(
            username="norole", password="test123"
        )

        # Assign roles
        self.admin_user.groups.add(self.admin_group)
        self.instructor_user.groups.add(self.instructor_group)
        self.student_user.groups.add(self.student_group)

    def test_get_user_role(self):
        """Test role detection for different users"""
        self.assertEqual(get_user_role(self.admin_user), ROLE_ADMIN)
        self.assertEqual(get_user_role(self.instructor_user), ROLE_INSTRUCTOR)
        self.assertEqual(get_user_role(self.student_user), ROLE_STUDENT)
        self.assertIsNone(get_user_role(self.no_role_user))

    def test_superuser_is_admin(self):
        """Test that superuser is automatically considered admin"""
        superuser = User.objects.create_superuser(username="super", password="test123")
        self.assertEqual(get_user_role(superuser), ROLE_ADMIN)


class LabRequestRBACTest(APITestCase):
    """Test RBAC for LabRequest operations"""

    def setUp(self):
        self.client = APIClient()

        # Create user groups
        self.admin_group = Group.objects.get(name="admin")
        self.instructor_group = Group.objects.get(name="instructor")
        self.student_group = Group.objects.get(name="student")

        # Create test users
        self.admin_user = User.objects.create_user(username="admin", password="test123")
        self.instructor_user = User.objects.create_user(
            username="instructor", password="test123"
        )
        self.student_user = User.objects.create_user(
            username="student", password="test123"
        )

        # Assign roles
        self.admin_user.groups.add(self.admin_group)
        self.instructor_user.groups.add(self.instructor_group)
        self.student_user.groups.add(self.student_group)

        # Create test patient
        self.patient = Patient.objects.create(
            first_name="Test",
            last_name="Patient",
            date_of_birth="1990-01-01",
            email="test@example.com",
        )

        # Create test lab request
        self.lab_request = LabRequest.objects.create(
            patient=self.patient,
            user=self.student_user,
            test_type="Blood Test",
            reason="Routine blood work",
            status="pending",
        )

    def test_student_can_create_lab_request(self):
        """Test that students can create lab requests"""
        self.client.force_authenticate(user=self.student_user)
        data = {
            "patient": self.patient.id,
            "test_type": "X-Ray",
            "reason": "Patient complaining of chest pain",
            "status": "pending",
        }
        response = self.client.post("/api/student-groups/lab-requests/", data)
        if response.status_code != status.HTTP_201_CREATED:
            print(f"Response status: {response.status_code}")
            print(f"Response data: {response.data}")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["user"], self.student_user.id)

    def test_student_can_list_own_lab_requests(self):
        """Test that students can list their own lab requests"""
        self.client.force_authenticate(user=self.student_user)
        response = self.client.get("/api/student-groups/lab-requests/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should only see their own requests
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["user"], self.student_user.id)

    def test_student_cannot_update_lab_request(self):
        """Test that students cannot update lab requests"""
        self.client.force_authenticate(user=self.student_user)
        data = {"status": "completed"}
        response = self.client.patch(
            f"/api/student-groups/lab-requests/{self.lab_request.id}/", data
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_instructor_can_create_lab_request(self):
        """Test that instructors can create lab requests"""
        self.client.force_authenticate(user=self.instructor_user)
        data = {
            "patient": self.patient.id,
            "user": self.student_user.id,  # Instructor can assign to any user
            "test_type": "MRI",
            "reason": "Patient needs MRI scan for diagnosis",
            "status": "pending",
        }
        response = self.client.post("/api/instructors/lab-requests/", data)
        if response.status_code != status.HTTP_201_CREATED:
            print(f"Response status: {response.status_code}")
            print(f"Response data: {response.data}")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_instructor_can_list_lab_requests(self):
        """Test that instructors can list lab requests"""
        self.client.force_authenticate(user=self.instructor_user)
        response = self.client.get("/api/instructors/lab-requests/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_instructor_can_retrieve_lab_request(self):
        """Test that instructors can retrieve specific lab requests"""
        self.client.force_authenticate(user=self.instructor_user)
        # Ensure we have a LabRequest to retrieve
        test_request = LabRequest.objects.create(
            patient=self.patient,
            user=self.student_user,
            test_type="Test Retrieval",
            reason="Testing instructor retrieval capabilities",
            status="pending",
        )
        response = self.client.get(f"/api/instructors/lab-requests/{test_request.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_instructor_can_update_lab_request(self):
        """Test that instructors can update lab request via instructor endpoints"""
        self.client.force_authenticate(user=self.instructor_user)
        # Use instructor endpoint for updates
        data = {"status": "completed"}
        response = self.client.patch(
            f"/api/instructors/lab-requests/{self.lab_request.id}/", data
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify the field was updated
        self.lab_request.refresh_from_db()
        self.assertEqual(self.lab_request.status, "completed")

    def test_admin_has_full_access(self):
        """Test that admin users have full access to lab requests"""
        self.client.force_authenticate(user=self.admin_user)

        # Create a fresh LabRequest for admin testing
        admin_request = LabRequest.objects.create(
            patient=self.patient,
            user=self.student_user,
            test_type="Admin Test",
            reason="Testing admin access rights",
            status="pending",
        )

        # Can list through instructor endpoint (admin inherits instructor permissions)
        response = self.client.get("/api/instructors/lab-requests/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Can retrieve through instructor endpoint
        response = self.client.get(f"/api/instructors/lab-requests/{admin_request.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Can update through instructor endpoint
        data = {"status": "completed"}
        response = self.client.patch(
            f"/api/instructors/lab-requests/{admin_request.id}/", data
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Can delete through instructor endpoint
        response = self.client.delete(
            f"/api/instructors/lab-requests/{admin_request.id}/"
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)


class PatientRBACTest(APITestCase):
    """Test RBAC for Patient operations"""

    def setUp(self):
        self.client = APIClient()

        # Create user groups
        self.admin_group = Group.objects.get(name="admin")
        self.instructor_group = Group.objects.get(name="instructor")
        self.student_group = Group.objects.get(name="student")

        # Create test users
        self.admin_user = User.objects.create_user(username="admin", password="test123")
        self.instructor_user = User.objects.create_user(
            username="instructor", password="test123"
        )
        self.student_user = User.objects.create_user(
            username="student", password="test123"
        )

        # Assign roles
        self.admin_user.groups.add(self.admin_group)
        self.instructor_user.groups.add(self.instructor_group)
        self.student_user.groups.add(self.student_group)

        # Create test patient
        self.patient = Patient.objects.create(
            first_name="Test",
            last_name="Patient",
            date_of_birth="1990-01-01",
            email="test@example.com",
        )

    def test_student_can_read_patients(self):
        """Test that students can read patient data"""
        self.client.force_authenticate(user=self.student_user)

        # Can list patients
        response = self.client.get(reverse("patient-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Can retrieve specific patient
        response = self.client.get(reverse("patient-detail", args=[self.patient.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_student_cannot_modify_patients(self):
        """Test that students cannot modify patient data"""
        self.client.force_authenticate(user=self.student_user)

        # Cannot create
        data = {
            "first_name": "New",
            "last_name": "Patient",
            "date_of_birth": "1985-01-01",
            "email": "new@example.com",
        }
        response = self.client.post(reverse("patient-list"), data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Cannot update
        data = {"first_name": "Updated"}
        response = self.client.patch(
            reverse("patient-detail", args=[self.patient.id]), data
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Cannot delete
        response = self.client.delete(reverse("patient-detail", args=[self.patient.id]))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_instructor_can_read_patients(self):
        """Test that instructors can read patient data"""
        self.client.force_authenticate(user=self.instructor_user)

        # Can list patients
        response = self.client.get(reverse("patient-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Can retrieve specific patient
        response = self.client.get(reverse("patient-detail", args=[self.patient.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_instructor_can_modify_patients(self):
        """Test that instructors can modify patient data"""
        self.client.force_authenticate(user=self.instructor_user)

        # Can create
        data = {
            "first_name": "New",
            "last_name": "Patient",
            "date_of_birth": "1985-01-01",
            "email": "new@example.com",
        }
        response = self.client.post(reverse("patient-list"), data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Can update
        data = {"first_name": "Updated"}
        response = self.client.patch(
            reverse("patient-detail", args=[self.patient.id]), data
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify update
        self.patient.refresh_from_db()
        self.assertEqual(self.patient.first_name, "Updated")

        # Can delete (create a new patient to delete to avoid affecting other tests)
        create_response = self.client.post(
            reverse("patient-list"),
            {
                "first_name": "To Delete",
                "last_name": "Patient",
                "date_of_birth": "1985-01-01",
                "email": "delete@example.com",
            },
        )
        new_patient_id = create_response.data["id"]
        response = self.client.delete(reverse("patient-detail", args=[new_patient_id]))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_admin_can_modify_patients(self):
        """Test that admin users can modify patient data"""
        self.client.force_authenticate(user=self.admin_user)

        # Can create
        data = {
            "first_name": "New",
            "last_name": "Patient",
            "date_of_birth": "1985-01-01",
            "email": "new@example.com",
        }
        response = self.client.post(reverse("patient-list"), data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Can update
        data = {"first_name": "Updated"}
        response = self.client.patch(
            reverse("patient-detail", args=[self.patient.id]), data
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Can delete
        response = self.client.delete(reverse("patient-detail", args=[self.patient.id]))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
