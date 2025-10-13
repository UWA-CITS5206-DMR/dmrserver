"""
Integration tests for approved_files API functionality.

Tests verify that:
1. ImagingRequest and BloodTestRequest return approved_files in API responses
2. Students can see approved_files in their completed requests
3. Instructors can see approved_files when managing requests
"""

import shutil
import tempfile

from django.contrib.auth.models import Group, User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from rest_framework import status
from rest_framework.test import APIClient

from patients.models import File, Patient
from student_groups.models import ApprovedFile, BloodTestRequest, ImagingRequest

# Create a temporary directory for test media files
TEST_MEDIA_ROOT = tempfile.mkdtemp()


@override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT)
class ApprovedFilesAPITestCase(TestCase):
    """Test that approved_files are correctly returned in API responses."""

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.test_media_root = TEST_MEDIA_ROOT

    @classmethod
    def tearDownClass(cls) -> None:
        super().tearDownClass()
        # Clean up the temporary media directory
        shutil.rmtree(cls.test_media_root, ignore_errors=True)

    @classmethod
    def setUpTestData(cls) -> None:
        # Reuse client-independent data across tests
        # Use a separate APIClient instance because Django TestCase sets self.client
        # to a django.test.Client in setUp(), which doesn't have force_authenticate.
        cls.api_client = APIClient()

        # Get or create groups
        cls.student_group, _ = Group.objects.get_or_create(name="student")
        cls.instructor_group, _ = Group.objects.get_or_create(name="instructor")

        # Create users
        cls.student_user = User.objects.create_user(
            username="student1",
            password="testpass123",
        )
        cls.student_user.groups.add(cls.student_group)

        cls.instructor_user = User.objects.create_user(
            username="instructor1",
            password="testpass123",
        )
        cls.instructor_user.groups.add(cls.instructor_group)

        # Create a patient
        cls.patient = Patient.objects.create(
            first_name="John",
            last_name="Doe",
            date_of_birth="1990-01-01",
            mrn="MRN200",
            ward="Ward C",
            bed="Bed 3",
            email="john.doe@example.com",
            phone_number="1234567890",
        )

        # Create test files once for reuse
        cls.file1 = File.objects.create(
            patient=cls.patient,
            file=SimpleUploadedFile(
                "test_file1.pdf",
                b"pdf1",
                content_type="application/pdf",
            ),
            display_name="Test File 1.pdf",
            requires_pagination=True,
            category=File.Category.IMAGING,
        )

        cls.file2 = File.objects.create(
            patient=cls.patient,
            file=SimpleUploadedFile(
                "test_file2.pdf",
                b"pdf2",
                content_type="application/pdf",
            ),
            display_name="Test File 2.pdf",
            requires_pagination=False,
            category=File.Category.LAB_RESULTS,
        )

    def _create_dummy_file(self, filename):
        """Create a valid dummy PDF file for testing."""
        from tests.test_utils import create_test_pdf

        content = create_test_pdf(num_pages=1)
        return SimpleUploadedFile(filename, content, content_type="application/pdf")

    def test_imaging_request_returns_approved_files_for_instructor(self) -> None:
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

        # Authenticate as instructor using DRF APIClient
        self.api_client.force_authenticate(user=self.instructor_user)

        # Retrieve the request
        response = self.api_client.get(
            f"/api/instructors/imaging-requests/{imaging_request.id}/",
        )

        assert response.status_code == status.HTTP_200_OK
        assert "approved_files" in response.data
        assert len(response.data["approved_files"]) == 2

        # Verify approved_files structure
        approved_files = response.data["approved_files"]
        assert str(approved_files[0]["file_id"]) == str(self.file1.id)
        assert approved_files[0]["page_range"] == "1-5"
        assert approved_files[0]["display_name"] == "Test File 1.pdf"
        assert approved_files[0]["requires_pagination"]

        assert str(approved_files[1]["file_id"]) == str(self.file2.id)
        assert approved_files[1]["page_range"] == ""
        assert approved_files[1]["display_name"] == "Test File 2.pdf"
        assert not approved_files[1]["requires_pagination"]

    def test_blood_test_request_returns_approved_files_for_instructor(self) -> None:
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

        # Authenticate as instructor using DRF APIClient
        self.api_client.force_authenticate(user=self.instructor_user)

        # Retrieve the request
        response = self.api_client.get(
            f"/api/instructors/blood-test-requests/{blood_test_request.id}/",
        )

        assert response.status_code == status.HTTP_200_OK
        assert "approved_files" in response.data
        assert len(response.data["approved_files"]) == 1

        # Verify approved_files structure
        approved_files = response.data["approved_files"]
        assert str(approved_files[0]["file_id"]) == str(self.file2.id)
        assert approved_files[0]["page_range"] == ""
        assert approved_files[0]["display_name"] == "Test File 2.pdf"

    def test_student_can_see_approved_files_in_completed_imaging_request(self) -> None:
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

        # Authenticate as student using DRF APIClient
        self.api_client.force_authenticate(user=self.student_user)

        # Retrieve the request
        response = self.api_client.get(
            f"/api/student-groups/imaging-requests/{imaging_request.id}/",
        )

        assert response.status_code == status.HTTP_200_OK
        assert "approved_files" in response.data
        assert len(response.data["approved_files"]) == 1

        # Verify approved_files structure
        approved_files = response.data["approved_files"]
        assert str(approved_files[0]["file_id"]) == str(self.file1.id)
        assert approved_files[0]["page_range"] == "1-3"
        assert "file_url" in approved_files[0]

    def test_imaging_request_list_returns_approved_files(self) -> None:
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
        # Authenticate as instructor using DRF APIClient
        self.api_client.force_authenticate(user=self.instructor_user)

        # List all requests
        response = self.api_client.get("/api/instructors/imaging-requests/")

        assert response.status_code == status.HTTP_200_OK
        results = response.data["results"]
        assert len(results) == 2

        # Find the completed request in results
        completed_request = next(r for r in results if r["status"] == "completed")
        assert "approved_files" in completed_request
        assert len(completed_request["approved_files"]) == 1

        # Find the pending request in results
        pending_request = next(r for r in results if r["status"] == "pending")
        assert "approved_files" in pending_request
        assert len(pending_request["approved_files"]) == 0

    def test_empty_approved_files_list_when_no_files_approved(self) -> None:
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

        # Authenticate as instructor using DRF APIClient
        self.api_client.force_authenticate(user=self.instructor_user)

        # Retrieve the request
        response = self.api_client.get(
            f"/api/instructors/imaging-requests/{imaging_request.id}/",
        )

        assert response.status_code == status.HTTP_200_OK
        assert "approved_files" in response.data
        assert response.data["approved_files"] == []
