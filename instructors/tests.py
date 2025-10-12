from django.conf import settings
from django.contrib.auth.models import User, Group
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from rest_framework.test import APITestCase
from rest_framework import status
from patients.models import Patient, File
from student_groups.models import ImagingRequest, BloodTestRequest, ApprovedFile
from core.context import Role
import tempfile
import shutil


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
            mrn="MRN300",
            ward="Ward D",
            bed="Bed 4",
            email="john@example.com",
        )

        self.imaging_request = ImagingRequest.objects.create(
            patient=self.patient,
            user=self.student_user,
            test_type="Blood Test",
            details="Instructor test case setup",
            infection_control_precautions=ImagingRequest.InfectionControlPrecaution.NONE,
            imaging_focus="Chest",
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
            mrn="MRN301",
            ward="Ward E",
            bed="Bed 5",
            email="jane@example.com",
        )

        self.blood_test_request = BloodTestRequest.objects.create(
            patient=self.patient,
            user=self.student_user,
            test_type="Complete Blood Count",
            details="Routine checkup",
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


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class ApprovedFilesTestCase(APITestCase):
    """
    Test cases for approved_files handling with flat file_id structure.
    This tests the fix for instructors approving requests with file_id only.
    """

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(settings.MEDIA_ROOT, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        self.instructor_group, created = Group.objects.get_or_create(
            name=Role.INSTRUCTOR.value
        )

        self.instructor_user = User.objects.create_user(
            username="instructor_file_test", password="testpass123"
        )
        self.instructor_user.groups.add(self.instructor_group)

        self.student_user = User.objects.create_user(
            username="student_file_test", password="testpass123"
        )

        self.patient = Patient.objects.create(
            first_name="Test",
            last_name="Patient",
            date_of_birth="2000-01-01",
            mrn="MRN302",
            ward="Ward F",
            bed="Bed 6",
            email="test@example.com",
        )

        # Create test files
        test_file_content = b"Test file content"
        self.file1 = File.objects.create(
            patient=self.patient,
            file=SimpleUploadedFile("test1.txt", test_file_content),
            display_name="Test File 1",
            requires_pagination=False,
        )

        self.file2 = File.objects.create(
            patient=self.patient,
            file=SimpleUploadedFile("test2.pdf", test_file_content),
            display_name="Test File 2 (PDF)",
            requires_pagination=True,
        )

        self.imaging_request = ImagingRequest.objects.create(
            patient=self.patient,
            user=self.student_user,
            test_type="X-ray",
            details="Test request",
            infection_control_precautions=ImagingRequest.InfectionControlPrecaution.NONE,
            imaging_focus="Arm",
            name="Dr. Test",
            role="Doctor",
            status="pending",
        )

        self.blood_test_request = BloodTestRequest.objects.create(
            patient=self.patient,
            user=self.student_user,
            test_type="FBC",
            details="Test blood test",
            name="Dr. Test",
            role="Doctor",
            status="pending",
        )

    def test_imaging_request_approval_with_flat_file_id_structure(self):
        """
        Test that instructors can approve imaging requests with flat file_id structure.
        Frontend sends: {"status": "completed", "approved_files": [{"file_id": "uuid", "page_range": "1-5"}]}
        """
        self.client.force_authenticate(user=self.instructor_user)

        # Approve the request with flat file_id structure
        response = self.client.patch(
            f"/api/instructors/imaging-requests/{self.imaging_request.id}/",
            {
                "status": "completed",
                "approved_files": [
                    {
                        "file_id": str(self.file2.id),
                        "page_range": "1-5",
                    }
                ],
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify the request status was updated
        self.imaging_request.refresh_from_db()
        self.assertEqual(self.imaging_request.status, "completed")

        # Verify the approved file was created
        approved_files = ApprovedFile.objects.filter(
            imaging_request=self.imaging_request
        )
        self.assertEqual(approved_files.count(), 1)
        self.assertEqual(approved_files.first().file.id, self.file2.id)
        self.assertEqual(approved_files.first().page_range, "1-5")

    def test_imaging_request_approval_with_file_id_only(self):
        """
        Test approval with only file_id (no page_range) for non-paginated files.
        """
        self.client.force_authenticate(user=self.instructor_user)

        response = self.client.patch(
            f"/api/instructors/imaging-requests/{self.imaging_request.id}/",
            {
                "status": "completed",
                "approved_files": [
                    {
                        "file_id": str(self.file1.id),
                    }
                ],
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify the approved file was created without page_range
        approved_files = ApprovedFile.objects.filter(
            imaging_request=self.imaging_request
        )
        self.assertEqual(approved_files.count(), 1)
        self.assertEqual(approved_files.first().file.id, self.file1.id)
        self.assertIsNone(approved_files.first().page_range)

    def test_blood_test_request_approval_with_flat_file_id(self):
        """
        Test that blood test request approval works with flat file_id structure.
        Note: BloodTestRequest uses direct M2M, so page_range is not applicable.
        """
        self.client.force_authenticate(user=self.instructor_user)

        response = self.client.patch(
            f"/api/instructors/blood-test-requests/{self.blood_test_request.id}/",
            {
                "status": "completed",
                "approved_files": [
                    {
                        "file_id": str(self.file1.id),
                    }
                ],
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify the request status was updated
        self.blood_test_request.refresh_from_db()
        self.assertEqual(self.blood_test_request.status, "completed")

        # Verify the approved file was added (direct M2M)
        self.assertEqual(self.blood_test_request.approved_files.count(), 1)
        self.assertEqual(
            self.blood_test_request.approved_files.first().id, self.file1.id
        )

    def test_multiple_approved_files(self):
        """
        Test approving a request with multiple files.
        """
        self.client.force_authenticate(user=self.instructor_user)

        response = self.client.patch(
            f"/api/instructors/imaging-requests/{self.imaging_request.id}/",
            {
                "status": "completed",
                "approved_files": [
                    {"file_id": str(self.file1.id)},
                    {"file_id": str(self.file2.id), "page_range": "1-3"},
                ],
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify multiple approved files were created
        approved_files = ApprovedFile.objects.filter(
            imaging_request=self.imaging_request
        )
        self.assertEqual(approved_files.count(), 2)

    def test_validation_error_for_missing_page_range_on_paginated_file(self):
        """
        Test that validation error is raised when page_range is missing for paginated files.
        """
        self.client.force_authenticate(user=self.instructor_user)

        response = self.client.patch(
            f"/api/instructors/imaging-requests/{self.imaging_request.id}/",
            {
                "status": "completed",
                "approved_files": [
                    {
                        "file_id": str(self.file2.id),  # file2 requires pagination
                    }
                ],
            },
            format="json",
        )

        # Should fail validation
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_clear_approved_files_with_empty_list(self):
        """
        Test that passing an empty approved_files list clears existing files.
        """
        self.client.force_authenticate(user=self.instructor_user)

        # First, approve with a file
        self.client.patch(
            f"/api/instructors/imaging-requests/{self.imaging_request.id}/",
            {
                "status": "completed",
                "approved_files": [{"file_id": str(self.file1.id)}],
            },
            format="json",
        )

        # Verify file was added
        self.assertEqual(
            ApprovedFile.objects.filter(imaging_request=self.imaging_request).count(), 1
        )

        # Now clear with empty list
        response = self.client.patch(
            f"/api/instructors/imaging-requests/{self.imaging_request.id}/",
            {"approved_files": []},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify files were cleared
        self.assertEqual(
            ApprovedFile.objects.filter(imaging_request=self.imaging_request).count(), 0
        )
