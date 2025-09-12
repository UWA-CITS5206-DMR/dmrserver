from django.contrib.auth.models import User, Group
from rest_framework.test import APITestCase
from rest_framework import status
from patients.models import Patient
from student_groups.models import LabRequest
from core.permissions import ROLE_INSTRUCTOR, ROLE_STUDENT


class InstructorViewSetTestCase(APITestCase):
    def setUp(self):
        self.instructor_group, created = Group.objects.get_or_create(
            name=ROLE_INSTRUCTOR
        )
        self.student_group, created = Group.objects.get_or_create(name=ROLE_STUDENT)

        self.instructor_user = User.objects.create_user(
            username="instructor1", password="testpass123"
        )
        self.instructor_user.groups.add(self.instructor_group)

        self.student_user = User.objects.create_user(
            username="student1", password="testpass123"
        )
        self.student_user.groups.add(self.student_group)

        self.patient = Patient.objects.create(
            first_name="John",
            last_name="Doe",
            date_of_birth="1990-01-01",
            email="john@example.com",
        )

        self.lab_request = LabRequest.objects.create(
            patient=self.patient,
            user=self.student_user,
            test_type="Blood Test",
            reason="Instructor test case setup",
            status="pending",
        )

    def test_instructor_can_view_lab_requests(self):
        self.client.force_authenticate(user=self.instructor_user)
        response = self.client.get("/api/instructors/lab-requests/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)

    def test_instructor_can_update_lab_request_status(self):
        self.client.force_authenticate(user=self.instructor_user)
        response = self.client.patch(
            f"/api/instructors/lab-requests/{self.lab_request.id}/",
            {"status": "completed"},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.lab_request.refresh_from_db()
        self.assertEqual(self.lab_request.status, "completed")

    def test_instructor_dashboard_access(self):
        self.client.force_authenticate(user=self.instructor_user)
        response = self.client.get("/api/instructors/dashboard/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("patients_count", response.data)
        self.assertIn("total_lab_requests", response.data)
        self.assertEqual(response.data["patients_count"], 1)

    def test_pending_lab_requests_endpoint(self):
        self.client.force_authenticate(user=self.instructor_user)
        response = self.client.get("/api/instructors/lab-requests/pending/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Check if response has pagination (results key) or direct array
        if "results" in response.data:
            self.assertEqual(len(response.data["results"]), 1)
        else:
            self.assertEqual(len(response.data), 1)

    def test_lab_request_stats_endpoint(self):
        self.client.force_authenticate(user=self.instructor_user)
        response = self.client.get("/api/instructors/lab-requests/stats/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["total"], 1)
        self.assertEqual(response.data["pending"], 1)
        self.assertEqual(response.data["completed"], 0)

    def test_student_cannot_access_instructor_endpoints(self):
        self.client.force_authenticate(user=self.student_user)
        response = self.client.get("/api/instructors/lab-requests/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_unauthorized_access_denied(self):
        response = self.client.get("/api/instructors/lab-requests/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_non_instructor_dashboard_access_denied(self):
        self.client.force_authenticate(user=self.student_user)
        response = self.client.get("/api/instructors/dashboard/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        response = self.client.get("/api/instructors/dashboard/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
