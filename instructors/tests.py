import shutil
import tempfile

from django.conf import settings
from django.contrib.auth.models import Group, User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APITestCase

from core.context import Role
from patients.models import File, Patient
from student_groups.models import ApprovedFile, BloodTestRequest, ImagingRequest


class InstructorViewSetTestCase(APITestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        # Shared fixtures that are immutable across tests
        cls.instructor_group, _ = Group.objects.get_or_create(
            name=Role.INSTRUCTOR.value,
        )
        cls.student_group, _ = Group.objects.get_or_create(name=Role.STUDENT.value)

        cls.instructor_user = User.objects.create_user(
            username="instructor1",
            password="testpass123",
        )
        cls.instructor_user.groups.add(cls.instructor_group)

        cls.student_user = User.objects.create_user(
            username="student1",
            password="testpass123",
        )
        cls.student_user.groups.add(cls.student_group)

        cls.patient = Patient.objects.create(
            first_name="John",
            last_name="Doe",
            date_of_birth="1990-01-01",
            mrn="MRN300",
            ward="Ward D",
            bed="Bed 4",
            phone_number="+6000000000",
        )

    def setUp(self) -> None:
        # Per-test mutable objects (requests) should stay in setUp
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

    def test_instructor_can_view_lab_requests(self) -> None:
        self.client.force_authenticate(user=self.instructor_user)
        response = self.client.get("/api/student-groups/imaging-requests/")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 1

    def test_instructor_can_update_lab_request_status(self) -> None:
        self.client.force_authenticate(user=self.instructor_user)
        response = self.client.patch(
            f"/api/student-groups/imaging-requests/{self.imaging_request.id}/",
            {"status": "completed"},
        )
        assert response.status_code == status.HTTP_200_OK
        self.imaging_request.refresh_from_db()
        assert self.imaging_request.status == "completed"

    def test_pending_lab_requests_endpoint(self) -> None:
        self.client.force_authenticate(user=self.instructor_user)
        response = self.client.get("/api/student-groups/imaging-requests/pending/")
        assert response.status_code == status.HTTP_200_OK
        # Check if response has pagination (results key) or direct array
        if "results" in response.data:
            assert len(response.data["results"]) == 1
        else:
            assert len(response.data) == 1

    def test_lab_request_stats_endpoint(self) -> None:
        self.client.force_authenticate(user=self.instructor_user)
        response = self.client.get("/api/student-groups/imaging-requests/stats/")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["total"] == 1
        assert response.data["pending"] == 1
        assert response.data["completed"] == 0

    def test_student_cannot_modify_investigation_requests(self) -> None:
        self.client.force_authenticate(user=self.student_user)
        response = self.client.patch(
            f"/api/student-groups/imaging-requests/{self.imaging_request.id}/",
            {"status": "completed"},
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_unauthorized_access_denied(self) -> None:
        response = self.client.get("/api/student-groups/imaging-requests/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_imaging_request_returns_full_user_and_patient_details(self) -> None:
        """
        Test that GET requests return full user and patient objects, not just IDs.
        """
        self.client.force_authenticate(user=self.instructor_user)
        response = self.client.get(
            f"/api/student-groups/imaging-requests/{self.imaging_request.id}/",
        )
        assert response.status_code == status.HTTP_200_OK

        # Verify user is a full object with expected fields
        assert "user" in response.data
        assert isinstance(response.data["user"], dict)
        assert "id" in response.data["user"]
        assert "username" in response.data["user"]
        assert "email" in response.data["user"]
        assert response.data["user"]["username"] == "student1"

        # Verify patient is a full object with expected fields
        assert "patient" in response.data
        assert isinstance(response.data["patient"], dict)
        assert "id" in response.data["patient"]
        assert "first_name" in response.data["patient"]
        assert "last_name" in response.data["patient"]
        assert "mrn" in response.data["patient"]
        assert "phone_number" in response.data["patient"]
        assert response.data["patient"]["first_name"] == "John"
        assert response.data["patient"]["last_name"] == "Doe"

    def test_imaging_request_list_returns_full_user_and_patient_details(self) -> None:
        """
        Test that list endpoint also returns full user and patient objects.
        """
        self.client.force_authenticate(user=self.instructor_user)
        response = self.client.get("/api/student-groups/imaging-requests/")
        assert response.status_code == status.HTTP_200_OK

        first_item = response.data["results"][0]

        # Verify user is a full object
        assert isinstance(first_item["user"], dict)
        assert "username" in first_item["user"]
        assert first_item["user"]["username"] == "student1"

        # Verify patient is a full object
        assert isinstance(first_item["patient"], dict)
        assert "first_name" in first_item["patient"]
        assert first_item["patient"]["first_name"] == "John"

    def test_instructor_can_list_student_groups(self) -> None:
        self.client.force_authenticate(user=self.instructor_user)
        response = self.client.get("/api/instructors/student-groups/")
        assert response.status_code == status.HTTP_200_OK
        assert isinstance(response.data, list)
        usernames = [entry["username"] for entry in response.data]
        assert "student1" in usernames

    def test_student_cannot_list_student_groups(self) -> None:
        self.client.force_authenticate(user=self.student_user)
        response = self.client.get("/api/instructors/student-groups/")
        assert response.status_code == status.HTTP_403_FORBIDDEN


class BloodTestRequestViewSetTestCase(APITestCase):
    """
    Test cases specifically for BloodTestRequest endpoints to verify
    full user and patient details are returned.
    """

    @classmethod
    def setUpTestData(cls) -> None:
        cls.instructor_group, _ = Group.objects.get_or_create(
            name=Role.INSTRUCTOR.value,
        )

        cls.instructor_user = User.objects.create_user(
            username="instructor2",
            password="testpass123",
        )
        cls.instructor_user.groups.add(cls.instructor_group)

        cls.student_user = User.objects.create_user(
            username="student2",
            password="testpass123",
        )

        cls.patient = Patient.objects.create(
            first_name="Jane",
            last_name="Smith",
            date_of_birth="1995-05-15",
            mrn="MRN301",
            ward="Ward E",
            bed="Bed 5",
        )

    def setUp(self) -> None:
        # Keep per-test mutable request objects here
        self.blood_test_request = BloodTestRequest.objects.create(
            patient=self.patient,
            user=self.student_user,
            test_type=BloodTestRequest.TestType.FBC,
            details="Routine checkup",
            name="Dr. Smith",
            role="Physician",
            status="pending",
        )

    def test_blood_test_request_returns_full_user_and_patient_details(self) -> None:
        """
        Test that GET requests return full user and patient objects, not just IDs.
        """
        self.client.force_authenticate(user=self.instructor_user)
        response = self.client.get(
            f"/api/student-groups/blood-test-requests/{self.blood_test_request.id}/",
        )
        assert response.status_code == status.HTTP_200_OK

        # Verify user is a full object with expected fields
        assert "user" in response.data
        assert isinstance(response.data["user"], dict)
        assert "username" in response.data["user"]
        assert response.data["user"]["username"] == "student2"

        # Verify patient is a full object with expected fields
        assert "patient" in response.data
        assert isinstance(response.data["patient"], dict)
        assert "first_name" in response.data["patient"]
        assert "last_name" in response.data["patient"]
        assert response.data["patient"]["first_name"] == "Jane"
        assert response.data["patient"]["last_name"] == "Smith"

    def test_blood_test_request_list_returns_full_details(self) -> None:
        """
        Test that list endpoint also returns full user and patient objects.
        """
        self.client.force_authenticate(user=self.instructor_user)
        response = self.client.get("/api/student-groups/blood-test-requests/")
        assert response.status_code == status.HTTP_200_OK

        first_item = response.data["results"][0]

        # Verify user is a full object
        assert isinstance(first_item["user"], dict)
        assert "username" in first_item["user"]

        # Verify patient is a full object
        assert isinstance(first_item["patient"], dict)
        assert "first_name" in first_item["patient"]


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class ApprovedFilesTestCase(APITestCase):
    """
    Test cases for approved_files handling with flat file_id structure.
    This tests the fix for instructors approving requests with file_id only.
    """

    @classmethod
    def tearDownClass(cls) -> None:
        shutil.rmtree(settings.MEDIA_ROOT, ignore_errors=True)
        super().tearDownClass()

    def setUp(self) -> None:
        # Only create per-test mutable request objects here; shared fixtures are in setUpTestData
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

    @classmethod
    def setUpTestData(cls) -> None:
        # Shared fixtures for approved files tests
        cls.instructor_group, _ = Group.objects.get_or_create(
            name=Role.INSTRUCTOR.value,
        )

        cls.instructor_user = User.objects.create_user(
            username="instructor_file_test",
            password="testpass123",
        )
        cls.instructor_user.groups.add(cls.instructor_group)

        cls.student_user = User.objects.create_user(
            username="student_file_test",
            password="testpass123",
        )

        cls.patient = Patient.objects.create(
            first_name="Test",
            last_name="Patient",
            date_of_birth="2000-01-01",
            mrn="MRN302",
            ward="Ward F",
            bed="Bed 6",
        )

        # Create test files once for the class to avoid repeated file writes
        test_file_content = b"Test file content"
        cls.file1 = File.objects.create(
            patient=cls.patient,
            file=SimpleUploadedFile("test1.txt", test_file_content),
            display_name="Test File 1",
            requires_pagination=False,
        )

        cls.file2 = File.objects.create(
            patient=cls.patient,
            file=SimpleUploadedFile("test2.pdf", test_file_content),
            display_name="Test File 2 (PDF)",
            requires_pagination=True,
        )

    def test_imaging_request_approval_with_flat_file_id_structure(self) -> None:
        """
        Test that instructors can approve imaging requests with flat file_id structure.
        Frontend sends: {"status": "completed", "approved_files": [{"file_id": "uuid", "page_range": "1-5"}]}
        """
        self.client.force_authenticate(user=self.instructor_user)

        # Approve the request with flat file_id structure
        response = self.client.patch(
            f"/api/student-groups/imaging-requests/{self.imaging_request.id}/",
            {
                "status": "completed",
                "approved_files": [
                    {
                        "file_id": str(self.file2.id),
                        "page_range": "1-5",
                    },
                ],
            },
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK

        # Verify the request status was updated
        self.imaging_request.refresh_from_db()
        assert self.imaging_request.status == "completed"

        # Verify the approved file was created
        approved_files = ApprovedFile.objects.filter(
            imaging_request=self.imaging_request,
        )
        assert approved_files.count() == 1
        assert approved_files.first().file.id == self.file2.id
        assert approved_files.first().page_range == "1-5"

    def test_imaging_request_approval_with_file_id_only(self) -> None:
        """
        Test approval with only file_id (no page_range) for non-paginated files.
        """
        self.client.force_authenticate(user=self.instructor_user)

        response = self.client.patch(
            f"/api/student-groups/imaging-requests/{self.imaging_request.id}/",
            {
                "status": "completed",
                "approved_files": [
                    {
                        "file_id": str(self.file1.id),
                    },
                ],
            },
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK

        # Verify the approved file was created without page_range
        approved_files = ApprovedFile.objects.filter(
            imaging_request=self.imaging_request,
        )
        assert approved_files.count() == 1
        assert approved_files.first().file.id == self.file1.id
        assert approved_files.first().page_range == ""

    def test_blood_test_request_approval_with_flat_file_id(self) -> None:
        """
        Test that blood test request approval works with flat file_id structure.
        Note: BloodTestRequest uses direct M2M, so page_range is not applicable.
        """
        self.client.force_authenticate(user=self.instructor_user)

        response = self.client.patch(
            f"/api/student-groups/blood-test-requests/{self.blood_test_request.id}/",
            {
                "status": "completed",
                "approved_files": [
                    {
                        "file_id": str(self.file1.id),
                    },
                ],
            },
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK

        # Verify the request status was updated
        self.blood_test_request.refresh_from_db()
        assert self.blood_test_request.status == "completed"

        # Verify the approved file was added (direct M2M)
        assert self.blood_test_request.approved_files.count() == 1
        assert self.blood_test_request.approved_files.first().id == self.file1.id

    def test_multiple_approved_files(self) -> None:
        """
        Test approving a request with multiple files.
        """
        self.client.force_authenticate(user=self.instructor_user)

        response = self.client.patch(
            f"/api/student-groups/imaging-requests/{self.imaging_request.id}/",
            {
                "status": "completed",
                "approved_files": [
                    {"file_id": str(self.file1.id)},
                    {"file_id": str(self.file2.id), "page_range": "1-3"},
                ],
            },
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK

        # Verify multiple approved files were created
        approved_files = ApprovedFile.objects.filter(
            imaging_request=self.imaging_request,
        )
        assert approved_files.count() == 2

    def test_validation_error_for_missing_page_range_on_paginated_file(self) -> None:
        """
        Test that validation error is raised when page_range is missing for paginated files.
        """
        self.client.force_authenticate(user=self.instructor_user)

        response = self.client.patch(
            f"/api/student-groups/imaging-requests/{self.imaging_request.id}/",
            {
                "status": "completed",
                "approved_files": [
                    {
                        "file_id": str(self.file2.id),  # file2 requires pagination
                    },
                ],
            },
            format="json",
        )

        # Should fail validation
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_clear_approved_files_with_empty_list(self) -> None:
        """
        Test that passing an empty approved_files list clears existing files.
        """
        self.client.force_authenticate(user=self.instructor_user)

        # First, approve with a file
        self.client.patch(
            f"/api/student-groups/imaging-requests/{self.imaging_request.id}/",
            {
                "status": "completed",
                "approved_files": [{"file_id": str(self.file1.id)}],
            },
            format="json",
        )

        # Verify file was added
        assert (
            ApprovedFile.objects.filter(imaging_request=self.imaging_request).count()
            == 1
        )

        # Now clear with empty list
        response = self.client.patch(
            f"/api/student-groups/imaging-requests/{self.imaging_request.id}/",
            {"approved_files": []},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK

        # Verify files were cleared
        assert (
            ApprovedFile.objects.filter(imaging_request=self.imaging_request).count()
            == 0
        )



