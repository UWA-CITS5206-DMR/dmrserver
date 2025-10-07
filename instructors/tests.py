from django.contrib.auth.models import User, Group
from rest_framework.test import APITestCase
from rest_framework import status
from patients.models import Patient
from student_groups.models import ImagingRequest, BloodTestRequest
from core.context import Role


class InstructorViewSetTestCase(APITestCase):
    def setUp(self):
        self.instructor_group, created = Group.objects.get_or_create(
            name=Role.INSTRUCTOR.value
        )
        self.student_group, created = Group.objects.get_or_create(
            name=Role.STUDENT.value
        )

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

        self.imaging_request = ImagingRequest.objects.create(
            patient=self.patient,
            user=self.student_user,
            test_type="Blood Test",
            reason="Instructor test case setup",
            name="Dr. Test",
            role="Doctor",
            status="pending",
        )

    def test_instructor_can_view_lab_requests(self):
        self.client.force_authenticate(user=self.instructor_user)
        response = self.client.get("/api/instructors/imaging-requests/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)

    def test_instructor_can_update_lab_request_status(self):
        self.client.force_authenticate(user=self.instructor_user)
        response = self.client.patch(
            f"/api/instructors/imaging-requests/{self.imaging_request.id}/",
            {"status": "completed"},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.imaging_request.refresh_from_db()
        self.assertEqual(self.imaging_request.status, "completed")

    def test_instructor_dashboard_access(self):
        self.client.force_authenticate(user=self.instructor_user)
        response = self.client.get("/api/instructors/dashboard/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("patients_count", response.data)
        self.assertIn("total_imaging_requests", response.data)
        self.assertEqual(response.data["patients_count"], 1)

    def test_pending_lab_requests_endpoint(self):
        self.client.force_authenticate(user=self.instructor_user)
        response = self.client.get("/api/instructors/imaging-requests/pending/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Check if response has pagination (results key) or direct array
        if "results" in response.data:
            self.assertEqual(len(response.data["results"]), 1)
        else:
            self.assertEqual(len(response.data), 1)

    def test_lab_request_stats_endpoint(self):
        self.client.force_authenticate(user=self.instructor_user)
        response = self.client.get("/api/instructors/imaging-requests/stats/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["total"], 1)
        self.assertEqual(response.data["pending"], 1)
        self.assertEqual(response.data["completed"], 0)

    def test_student_cannot_access_instructor_endpoints(self):
        self.client.force_authenticate(user=self.student_user)
        response = self.client.get("/api/instructors/imaging-requests/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_unauthorized_access_denied(self):
        response = self.client.get("/api/instructors/imaging-requests/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_non_instructor_dashboard_access_denied(self):
        self.client.force_authenticate(user=self.student_user)
        response = self.client.get("/api/instructors/dashboard/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_imaging_request_returns_full_user_and_patient_details(self):
        """
        Test that GET requests return full user and patient objects, not just IDs.
        """
        self.client.force_authenticate(user=self.instructor_user)
        response = self.client.get(
            f"/api/instructors/imaging-requests/{self.imaging_request.id}/"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify user is a full object with expected fields
        self.assertIn("user", response.data)
        self.assertIsInstance(response.data["user"], dict)
        self.assertIn("id", response.data["user"])
        self.assertIn("username", response.data["user"])
        self.assertIn("email", response.data["user"])
        self.assertEqual(response.data["user"]["username"], "student1")
        
        # Verify patient is a full object with expected fields
        self.assertIn("patient", response.data)
        self.assertIsInstance(response.data["patient"], dict)
        self.assertIn("id", response.data["patient"])
        self.assertIn("first_name", response.data["patient"])
        self.assertIn("last_name", response.data["patient"])
        self.assertIn("email", response.data["patient"])
        self.assertEqual(response.data["patient"]["first_name"], "John")
        self.assertEqual(response.data["patient"]["last_name"], "Doe")

    def test_imaging_request_list_returns_full_user_and_patient_details(self):
        """
        Test that list endpoint also returns full user and patient objects.
        """
        self.client.force_authenticate(user=self.instructor_user)
        response = self.client.get("/api/instructors/imaging-requests/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        first_item = response.data["results"][0]
        
        # Verify user is a full object
        self.assertIsInstance(first_item["user"], dict)
        self.assertIn("username", first_item["user"])
        self.assertEqual(first_item["user"]["username"], "student1")
        
        # Verify patient is a full object
        self.assertIsInstance(first_item["patient"], dict)
        self.assertIn("first_name", first_item["patient"])
        self.assertEqual(first_item["patient"]["first_name"], "John")


class BloodTestRequestViewSetTestCase(APITestCase):
    """
    Test cases specifically for BloodTestRequest endpoints to verify
    full user and patient details are returned.
    """

    def setUp(self):
        self.instructor_group, created = Group.objects.get_or_create(
            name=Role.INSTRUCTOR.value
        )

        self.instructor_user = User.objects.create_user(
            username="instructor2", password="testpass123"
        )
        self.instructor_user.groups.add(self.instructor_group)

        self.student_user = User.objects.create_user(
            username="student2", password="testpass123"
        )

        self.patient = Patient.objects.create(
            first_name="Jane",
            last_name="Smith",
            date_of_birth="1995-05-15",
            email="jane@example.com",
        )

        self.blood_test_request = BloodTestRequest.objects.create(
            patient=self.patient,
            user=self.student_user,
            test_type="Complete Blood Count",
            reason="Routine checkup",
            name="Dr. Smith",
            role="Physician",
            status="pending",
        )

    def test_blood_test_request_returns_full_user_and_patient_details(self):
        """
        Test that GET requests return full user and patient objects, not just IDs.
        """
        self.client.force_authenticate(user=self.instructor_user)
        response = self.client.get(
            f"/api/instructors/blood-test-requests/{self.blood_test_request.id}/"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify user is a full object with expected fields
        self.assertIn("user", response.data)
        self.assertIsInstance(response.data["user"], dict)
        self.assertIn("username", response.data["user"])
        self.assertEqual(response.data["user"]["username"], "student2")

        # Verify patient is a full object with expected fields
        self.assertIn("patient", response.data)
        self.assertIsInstance(response.data["patient"], dict)
        self.assertIn("first_name", response.data["patient"])
        self.assertIn("last_name", response.data["patient"])
        self.assertEqual(response.data["patient"]["first_name"], "Jane")
        self.assertEqual(response.data["patient"]["last_name"], "Smith")

    def test_blood_test_request_list_returns_full_details(self):
        """
        Test that list endpoint also returns full user and patient objects.
        """
        self.client.force_authenticate(user=self.instructor_user)
        response = self.client.get("/api/instructors/blood-test-requests/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        first_item = response.data["results"][0]

        # Verify user is a full object
        self.assertIsInstance(first_item["user"], dict)
        self.assertIn("username", first_item["user"])

        # Verify patient is a full object
        self.assertIsInstance(first_item["patient"], dict)
        self.assertIn("first_name", first_item["patient"])
