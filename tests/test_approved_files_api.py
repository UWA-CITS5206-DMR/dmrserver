"""
Integration tests for approved_files API functionality.

Tests verify that:
1. ImagingRequest and BloodTestRequest return approved_files in API responses
2. Students can see approved_files in their completed requests
3. Instructors can see approved_files when managing requests
"""

import tempfile
import shutil
from django.test import TestCase, override_settings
from django.contrib.auth.models import User, Group
from rest_framework.test import APIClient
from rest_framework import status
from patients.models import Patient, File
from student_groups.models import ImagingRequest, BloodTestRequest, ApprovedFile


# Create a temporary directory for test media files
TEST_MEDIA_ROOT = tempfile.mkdtemp()


@override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT)
class ApprovedFilesAPITestCase(TestCase):
    """Test that approved_files are correctly returned in API responses."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.test_media_root = TEST_MEDIA_ROOT

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        # Clean up the temporary media directory
        shutil.rmtree(cls.test_media_root, ignore_errors=True)

    def setUp(self):
        """Set up test data for approved_files API tests."""
        self.client = APIClient()

        # Get or create groups (they are created by migration core.0001_create_user_roles)
        self.student_group, _ = Group.objects.get_or_create(name="student")
        self.instructor_group, _ = Group.objects.get_or_create(name="instructor")

        # Create users
        self.student_user = User.objects.create_user(
            username="student1", password="testpass123"
        )
        self.student_user.groups.add(self.student_group)

        self.instructor_user = User.objects.create_user(
            username="instructor1", password="testpass123"
        )
        self.instructor_user.groups.add(self.instructor_group)

        # Create a patient
        self.patient = Patient.objects.create(
            first_name="John",
            last_name="Doe",
            date_of_birth="1990-01-01",
            mrn="MRN200",
            ward="Ward C",
            bed="Bed 3",
            email="john.doe@example.com",
            phone_number="1234567890",
        )

        # Create test files
        self.file1 = File.objects.create(
            patient=self.patient,
            file=self._create_dummy_file("test_file1.pdf"),
            display_name="Test File 1.pdf",
            requires_pagination=True,
            category=File.Category.IMAGING,
        )

        self.file2 = File.objects.create(
            patient=self.patient,
            file=self._create_dummy_file("test_file2.pdf"),
            display_name="Test File 2.pdf",
            requires_pagination=False,
            category=File.Category.LAB_RESULTS,
        )

    def _create_dummy_file(self, filename):
        """Create a valid dummy PDF file for testing."""
        from django.core.files.uploadedfile import SimpleUploadedFile
        from tests.test_utils import create_test_pdf

        content = create_test_pdf(num_pages=1)
        return SimpleUploadedFile(filename, content, content_type="application/pdf")

    def test_imaging_request_returns_approved_files_for_instructor(self):
        """Test that instructors can see approved_files in ImagingRequest."""
        # Create an imaging request
        imaging_request = ImagingRequest.objects.create(
            patient=self.patient,
            user=self.student_user,
            test_type="X-Ray",
            details="Test reason",
            infection_control_precautions=ImagingRequest.InfectionControlPrecaution.NONE,
            imaging_focus="Chest",
            status="completed",
            name="Dr. Smith",
            role="Radiologist",
        )

        # Add approved files
        ApprovedFile.objects.create(
            imaging_request=imaging_request,
            file=self.file1,
            page_range="1-5",
        )
        ApprovedFile.objects.create(
            imaging_request=imaging_request,
            file=self.file2,
            page_range="",
        )

        # Authenticate as instructor
        self.client.force_authenticate(user=self.instructor_user)

        # Retrieve the request
        response = self.client.get(
            f"/api/instructors/imaging-requests/{imaging_request.id}/"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("approved_files", response.data)
        self.assertEqual(len(response.data["approved_files"]), 2)

        # Verify approved_files structure
        approved_files = response.data["approved_files"]
        self.assertEqual(str(approved_files[0]["file_id"]), str(self.file1.id))
        self.assertEqual(approved_files[0]["page_range"], "1-5")
        self.assertEqual(approved_files[0]["display_name"], "Test File 1.pdf")
        self.assertTrue(approved_files[0]["requires_pagination"])

        self.assertEqual(str(approved_files[1]["file_id"]), str(self.file2.id))
        self.assertEqual(approved_files[1]["page_range"], "")
        self.assertEqual(approved_files[1]["display_name"], "Test File 2.pdf")
        self.assertFalse(approved_files[1]["requires_pagination"])

    def test_blood_test_request_returns_approved_files_for_instructor(self):
        """Test that instructors can see approved_files in BloodTestRequest."""
        # Create a blood test request
        blood_test_request = BloodTestRequest.objects.create(
            patient=self.patient,
            user=self.student_user,
            test_type="CBC",
            details="Test reason",
            status="completed",
            name="Dr. Johnson",
            role="Lab Director",
        )

        # Add approved files
        ApprovedFile.objects.create(
            blood_test_request=blood_test_request,
            file=self.file2,
            page_range="",
        )

        # Authenticate as instructor
        self.client.force_authenticate(user=self.instructor_user)

        # Retrieve the request
        response = self.client.get(
            f"/api/instructors/blood-test-requests/{blood_test_request.id}/"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("approved_files", response.data)
        self.assertEqual(len(response.data["approved_files"]), 1)

        # Verify approved_files structure
        approved_files = response.data["approved_files"]
        self.assertEqual(str(approved_files[0]["file_id"]), str(self.file2.id))
        self.assertEqual(approved_files[0]["page_range"], "")
        self.assertEqual(approved_files[0]["display_name"], "Test File 2.pdf")

    def test_student_can_see_approved_files_in_completed_imaging_request(self):
        """Test that students can see approved_files in their completed imaging requests."""
        # Create an imaging request for the student
        imaging_request = ImagingRequest.objects.create(
            patient=self.patient,
            user=self.student_user,
            test_type="CT Scan",
            details="Test reason",
            infection_control_precautions=ImagingRequest.InfectionControlPrecaution.NONE,
            imaging_focus="Abdomen",
            status="completed",
            name="Dr. Smith",
            role="Radiologist",
        )

        # Add approved files
        ApprovedFile.objects.create(
            imaging_request=imaging_request,
            file=self.file1,
            page_range="1-3",
        )

        # Authenticate as student
        self.client.force_authenticate(user=self.student_user)

        # Retrieve the request
        response = self.client.get(
            f"/api/student-groups/imaging-requests/{imaging_request.id}/"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("approved_files", response.data)
        self.assertEqual(len(response.data["approved_files"]), 1)

        # Verify approved_files structure
        approved_files = response.data["approved_files"]
        self.assertEqual(str(approved_files[0]["file_id"]), str(self.file1.id))
        self.assertEqual(approved_files[0]["page_range"], "1-3")
        self.assertIn("file_url", approved_files[0])

    def test_imaging_request_list_returns_approved_files(self):
        """Test that listing imaging requests includes approved_files."""
        # Create multiple imaging requests
        imaging_request1 = ImagingRequest.objects.create(
            patient=self.patient,
            user=self.student_user,
            test_type="X-Ray",
            details="Test reason 1",
            infection_control_precautions=ImagingRequest.InfectionControlPrecaution.NONE,
            imaging_focus="Leg",
            status="completed",
            name="Dr. Smith",
            role="Radiologist",
        )
        ApprovedFile.objects.create(
            imaging_request=imaging_request1,
            file=self.file1,
            page_range="1-5",
        )

        ImagingRequest.objects.create(
            patient=self.patient,
            user=self.student_user,
            test_type="MRI",
            details="Test reason 2",
            infection_control_precautions=ImagingRequest.InfectionControlPrecaution.NONE,
            imaging_focus="Spine",
            status="pending",
            name="Dr. Jones",
            role="Radiologist",
        )

        # Authenticate as instructor
        self.client.force_authenticate(user=self.instructor_user)

        # List all requests
        response = self.client.get("/api/instructors/imaging-requests/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data["results"]
        self.assertEqual(len(results), 2)

        # Find the completed request in results
        completed_request = next(r for r in results if r["status"] == "completed")
        self.assertIn("approved_files", completed_request)
        self.assertEqual(len(completed_request["approved_files"]), 1)

        # Find the pending request in results
        pending_request = next(r for r in results if r["status"] == "pending")
        self.assertIn("approved_files", pending_request)
        self.assertEqual(len(pending_request["approved_files"]), 0)

    def test_empty_approved_files_list_when_no_files_approved(self):
        """Test that approved_files is an empty list when no files are approved."""
        # Create a pending imaging request
        imaging_request = ImagingRequest.objects.create(
            patient=self.patient,
            user=self.student_user,
            test_type="Ultrasound",
            details="Test reason",
            infection_control_precautions=ImagingRequest.InfectionControlPrecaution.NONE,
            imaging_focus="Abdomen",
            status="pending",
            name="Dr. Williams",
            role="Radiologist",
        )

        # Authenticate as instructor
        self.client.force_authenticate(user=self.instructor_user)

        # Retrieve the request
        response = self.client.get(
            f"/api/instructors/imaging-requests/{imaging_request.id}/"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("approved_files", response.data)
        self.assertEqual(response.data["approved_files"], [])
