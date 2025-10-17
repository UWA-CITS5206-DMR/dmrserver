"""Integration tests for file access permissions in real scenarios."""

import shutil
import tempfile

from django.contrib.auth.models import Group, User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from core.context import Role
from patients.models import File, Patient
from student_groups.models import ApprovedFile, ImagingRequest

TEST_MEDIA_ROOT = tempfile.mkdtemp()


@override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT)
class FileAccessIntegrationTest(TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls._media_root = TEST_MEDIA_ROOT

    @classmethod
    def tearDownClass(cls) -> None:
        shutil.rmtree(cls._media_root, ignore_errors=True)
        super().tearDownClass()

    @classmethod
    def setUpTestData(cls) -> None:
        # Create persistent data reused across tests to avoid repeated file I/O
        cls.admin_group, _ = Group.objects.get_or_create(name=Role.ADMIN.value)
        cls.instructor_group, _ = Group.objects.get_or_create(
            name=Role.INSTRUCTOR.value,
        )
        cls.student_group, _ = Group.objects.get_or_create(name=Role.STUDENT.value)

        # Create users
        cls.student = User.objects.create_user("student1", "student@test.com", "pass")
        cls.instructor = User.objects.create_user(
            "instructor1",
            "instructor@test.com",
            "pass",
        )
        cls.admin = User.objects.create_user("admin1", "admin@test.com", "pass")

        # Assign roles
        cls.student.groups.add(cls.student_group)
        cls.instructor.groups.add(cls.instructor_group)
        cls.admin.groups.add(cls.admin_group)

        # Create patient reused across tests
        cls.patient = Patient.objects.create(
            first_name="John",
            last_name="Doe",
            date_of_birth="1990-01-01",
            mrn="MRN100",
            ward="Ward X",
            bed="Bed 10",
            phone_number="+4000000000",
        )

        # Create a single PDF file stored in media root and reused by tests
        from tests.test_utils import create_test_pdf

        pdf_content = create_test_pdf(num_pages=5)
        # Cache PDF bytes for reuse by tests to avoid repeated PyPDF2 work
        cls._cached_pdf = pdf_content
        cls.file = File.objects.create(
            patient=cls.patient,
            file=SimpleUploadedFile(
                "test.pdf",
                pdf_content,
                content_type="application/pdf",
            ),
            display_name="Test PDF",
            requires_pagination=False,
        )

    def setUp(self) -> None:
        # Per-test data that may be mutated (requests, approved files)
        # Create imaging request
        self.imaging_request = ImagingRequest.objects.create(
            user=self.student,
            patient=self.patient,
            test_type=ImagingRequest.TestType.X_RAY,
            details="Test imaging request for file integration test",
            infection_control_precautions=ImagingRequest.InfectionControlPrecaution.NONE,
            imaging_focus="Chest",
            name="Dr. Test",
            role="Doctor",
            status="completed",
        )

        # Create approved file per test
        self.approved_file = ApprovedFile.objects.create(
            imaging_request=self.imaging_request,
            file=self.file,
            page_range="1-3",
        )

        self.client = APIClient()

    def _create_test_pdf(self):
        """Create a valid test PDF with multiple pages using PyPDF2"""
        # Reuse cached PDF bytes when possible to avoid regeneration
        cached = getattr(self.__class__, "_cached_pdf", None)
        if cached is not None:
            return cached

        from tests.test_utils import create_test_pdf

        # Create a 5-page PDF with proper structure to avoid warnings
        return create_test_pdf(num_pages=5)

    def test_student_can_access_approved_file(self) -> None:
        """Test that student can access file they have approval for"""
        self.client.force_authenticate(user=self.student)

        url = reverse(
            "file-view",
            kwargs={"patient_pk": self.patient.id, "pk": self.file.id},
        )

        response = self.client.get(url)

        # Should be successful
        assert response.status_code == status.HTTP_200_OK
        assert response["Content-Type"] == "application/pdf"

    def test_student_cannot_access_unapproved_file(self) -> None:
        """Test that student cannot access file without approval"""
        # Delete the approved file
        self.approved_file.delete()

        self.client.force_authenticate(user=self.student)

        url = reverse(
            "file-view",
            kwargs={"patient_pk": self.patient.id, "pk": self.file.id},
        )

        response = self.client.get(url)

        # Should be forbidden
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_instructor_can_access_any_file(self) -> None:
        """Test that instructor can access any file"""
        self.client.force_authenticate(user=self.instructor)

        url = reverse(
            "file-view",
            kwargs={"patient_pk": self.patient.id, "pk": self.file.id},
        )

        response = self.client.get(url)

        # Should be successful
        assert response.status_code == status.HTTP_200_OK
        assert response["Content-Type"] == "application/pdf"

    def test_student_page_range_enforcement(self) -> None:
        """Test that student can only access approved page range"""
        # Change file to require pagination
        self.file.requires_pagination = True
        self.file.save()

        self.client.force_authenticate(user=self.student)

        # Try to access page 4 (not in approved range 1-3)
        url = reverse(
            "file-view",
            kwargs={"patient_pk": self.patient.id, "pk": self.file.id},
        )

        response = self.client.get(url, {"page_range": "4"})

        # Should be forbidden
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_student_can_access_approved_pages(self) -> None:
        """Test that student can access pages within approved range"""
        # Change file to require pagination
        self.file.requires_pagination = True
        self.file.save()

        self.client.force_authenticate(user=self.student)

        # Try to access page 2 (within approved range 1-3)
        url = reverse(
            "file-view",
            kwargs={"patient_pk": self.patient.id, "pk": self.file.id},
        )

        response = self.client.get(url, {"page_range": "2"})

        # Should be successful
        assert response.status_code == status.HTTP_200_OK
        assert response["Content-Type"] == "application/pdf"

    def test_student_cannot_manage_files(self) -> None:
        """Test that student cannot perform CRUD operations on files"""
        self.client.force_authenticate(user=self.student)

        # Try to create a file
        url = reverse("file-list", kwargs={"patient_pk": self.patient.id})
        response = self.client.post(url, {})

        # Should be forbidden
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_instructor_can_manage_files(self) -> None:
        """Test that instructor can perform CRUD operations on files"""
        self.client.force_authenticate(user=self.instructor)

        # Try to list files
        url = reverse("file-list", kwargs={"patient_pk": self.patient.id})
        response = self.client.get(url)

        # Should be successful
        assert response.status_code == status.HTTP_200_OK

    def test_manual_release_makes_file_visible_to_student(self) -> None:
        """Instructors can manually release files to student groups."""
        # Remove existing approved file to ensure manual release is required
        self.approved_file.delete()

        self.client.force_authenticate(user=self.instructor)
        release_url = reverse(
            "file-release",
            kwargs={"patient_pk": self.patient.id, "pk": self.file.id},
        )
        response = self.client.post(
            release_url,
            {"student_group_ids": [self.student.id]},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        payload = response.json()
        assert payload["released_to"][0]["id"] == self.student.id

        # Student should now see the file in their list view
        self.client.force_authenticate(user=self.student)
        list_url = reverse("file-list", kwargs={"patient_pk": self.patient.id})
        list_response = self.client.get(list_url)
        assert list_response.status_code == status.HTTP_200_OK
        file_ids = {item["id"] for item in list_response.data["results"]}
        assert str(self.file.id) in file_ids

    def test_manual_release_requires_page_range_for_paginated_file(self) -> None:
        """Manual releases for paginated files must include a page range."""
        self.approved_file.delete()
        self.file.requires_pagination = True
        self.file.save()

        self.client.force_authenticate(user=self.instructor)
        release_url = reverse(
            "file-release",
            kwargs={"patient_pk": self.patient.id, "pk": self.file.id},
        )
        response = self.client.post(
            release_url,
            {"student_group_ids": [self.student.id]},
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_manual_release_page_range_limits_student_access(self) -> None:
        """Students are constrained to the manual release page range."""
        self.approved_file.delete()
        self.file.requires_pagination = True
        self.file.save()

        self.client.force_authenticate(user=self.instructor)
        release_url = reverse(
            "file-release",
            kwargs={"patient_pk": self.patient.id, "pk": self.file.id},
        )
        response = self.client.post(
            release_url,
            {
                "student_group_ids": [self.student.id],
                "page_range": "2-3",
            },
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK

        self.client.force_authenticate(user=self.student)
        view_url = reverse(
            "file-view",
            kwargs={"patient_pk": self.patient.id, "pk": self.file.id},
        )

        allowed = self.client.get(view_url, {"page_range": "2"})
        assert allowed.status_code == status.HTTP_200_OK

        forbidden = self.client.get(view_url, {"page_range": "1"})
        assert forbidden.status_code == status.HTTP_403_FORBIDDEN

    def test_instructor_custom_page_range_access(self) -> None:
        """
        Test that instructors can specify custom page ranges for paginated files.

        This verifies that instructors have unrestricted access and can view
        any page range they specify via query parameters, regardless of
        ApprovedFile settings.
        """
        # Enable pagination for the file
        self.file.requires_pagination = True
        self.file.save()

        self.client.force_authenticate(user=self.instructor)
        url = reverse(
            "file-view",
            kwargs={"patient_pk": self.patient.id, "pk": self.file.id},
        )

        # Test 1: Instructor can access a single page using page_range
        response = self.client.get(url, {"page_range": "5"})
        assert response.status_code == status.HTTP_200_OK
        assert response["Content-Type"] == "application/pdf"

        # Test 2: Instructor can access a custom range using page_range parameter
        response = self.client.get(url, {"page_range": "1-5"})
        assert response.status_code == status.HTTP_200_OK
        assert response["Content-Type"] == "application/pdf"

        # Test 3: Instructor can access pages outside student's approved range
        # Student approved range is "1-3", instructor should access page 4
        response = self.client.get(url, {"page_range": "4"})
        assert response.status_code == status.HTTP_200_OK
        assert response["Content-Type"] == "application/pdf"

        # Test 4: Instructor can access complex ranges
        response = self.client.get(url, {"page_range": "1-2,4-5"})
        assert response.status_code == status.HTTP_200_OK
        assert response["Content-Type"] == "application/pdf"

    def test_instructor_can_access_entire_paginated_file_without_page_range(
        self,
    ) -> None:
        """
        Test that instructors can access entire paginated file without specifying page_range.

        This is a performance improvement - instructors don't need to specify
        a page range if they want the entire file.
        """
        # Enable pagination for the file
        self.file.requires_pagination = True
        self.file.save()

        self.client.force_authenticate(user=self.instructor)
        url = reverse(
            "file-view",
            kwargs={"patient_pk": self.patient.id, "pk": self.file.id},
        )

        # Instructor can access entire file without page_range parameter
        response = self.client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response["Content-Type"] == "application/pdf"

    def test_admin_custom_page_range_access(self) -> None:
        """
        Test that admins can specify custom page ranges for paginated files.

        Similar to instructors, admins should have unrestricted access.
        """
        # Enable pagination for the file
        self.file.requires_pagination = True
        self.file.save()

        self.client.force_authenticate(user=self.admin)
        url = reverse(
            "file-view",
            kwargs={"patient_pk": self.patient.id, "pk": self.file.id},
        )

        # Admin can access any single page using page_range
        response = self.client.get(url, {"page_range": "5"})
        assert response.status_code == status.HTTP_200_OK
        assert response["Content-Type"] == "application/pdf"

        # Admin can access any range using page_range parameter
        response = self.client.get(url, {"page_range": "1-5"})
        assert response.status_code == status.HTTP_200_OK
        assert response["Content-Type"] == "application/pdf"

    def test_admin_can_access_entire_paginated_file_without_page_range(self) -> None:
        """
        Test that admins can access entire paginated file without specifying page_range.

        Similar to instructors, admins have unrestricted access.
        """
        # Enable pagination for the file
        self.file.requires_pagination = True
        self.file.save()

        self.client.force_authenticate(user=self.admin)
        url = reverse(
            "file-view",
            kwargs={"patient_pk": self.patient.id, "pk": self.file.id},
        )

        # Admin can access entire file without page_range parameter
        response = self.client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response["Content-Type"] == "application/pdf"

    def test_student_cannot_access_pages_outside_approved_range(self) -> None:
        """
        Test that students are restricted to their approved page range.

        This ensures the security model is maintained - students cannot
        bypass ApprovedFile restrictions.
        """
        # Enable pagination for the file
        self.file.requires_pagination = True
        self.file.save()

        self.client.force_authenticate(user=self.student)
        url = reverse(
            "file-view",
            kwargs={"patient_pk": self.patient.id, "pk": self.file.id},
        )

        # Student approved range is "1-3"
        # Test 1: Access within approved range should succeed
        response = self.client.get(url, {"page_range": "2"})
        assert response.status_code == status.HTTP_200_OK

        # Test 2: Access outside approved range should fail
        response = self.client.get(url, {"page_range": "4"})
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "not authorized" in response.content.decode().lower()

        # Test 3: Range partially outside approved range should fail
        response = self.client.get(url, {"page_range": "2-5"})
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "not authorized" in response.content.decode().lower()

    def test_student_can_access_approved_file_from_blood_test_request(self) -> None:
        """
        Test that students can access files from BloodTestRequest with ApprovedFile.

        This test ensures that file access works for both ImagingRequest and BloodTestRequest.
        Previously, paginated files from BloodTestRequest were not accessible to students.
        """
        from student_groups.models import BloodTestRequest

        # Create a new file for blood test
        pdf_content = self._create_test_pdf()
        blood_test_file = File.objects.create(
            patient=self.patient,
            file=SimpleUploadedFile(
                "blood_test.pdf",
                pdf_content,
                content_type="application/pdf",
            ),
            display_name="Blood Test Results",
            requires_pagination=False,
        )

        # Create blood test request
        blood_test_request = BloodTestRequest.objects.create(
            user=self.student,
            patient=self.patient,
            test_types=[BloodTestRequest.TestType.FBC],
            details="Test blood test request for file integration test",
            name="Dr. Lab",
            role="Pathologist",
            status="completed",
        )

        # Create approved file for blood test
        ApprovedFile.objects.create(
            blood_test_request=blood_test_request,
            file=blood_test_file,
            page_range="1-2",
        )

        # Student should be able to access the file
        self.client.force_authenticate(user=self.student)
        url = reverse(
            "file-view",
            kwargs={"patient_pk": self.patient.id, "pk": blood_test_file.id},
        )

        response = self.client.get(url)

        # Should be successful
        assert response.status_code == status.HTTP_200_OK
        assert response["Content-Type"] == "application/pdf"

    def test_student_can_access_paginated_file_from_blood_test_request(self) -> None:
        """
        Test that students can access paginated files from BloodTestRequest.

        This specifically tests the _get_authorized_page_range method for BloodTestRequest.
        """
        from student_groups.models import BloodTestRequest

        # Create a paginated file for blood test
        pdf_content = self._create_test_pdf()
        blood_test_file = File.objects.create(
            patient=self.patient,
            file=SimpleUploadedFile(
                "blood_test_paginated.pdf",
                pdf_content,
                content_type="application/pdf",
            ),
            display_name="Blood Test Results (Paginated)",
            requires_pagination=True,
        )

        # Create blood test request
        blood_test_request = BloodTestRequest.objects.create(
            user=self.student,
            patient=self.patient,
            test_types=[BloodTestRequest.TestType.EUC],
            details="Test paginated blood test file access",
            name="Dr. Lab",
            role="Pathologist",
            status="completed",
        )

        # Create approved file with page range
        ApprovedFile.objects.create(
            blood_test_request=blood_test_request,
            file=blood_test_file,
            page_range="2-4",
        )

        # Student should be able to access pages within approved range
        self.client.force_authenticate(user=self.student)
        url = reverse(
            "file-view",
            kwargs={"patient_pk": self.patient.id, "pk": blood_test_file.id},
        )

        # Test 1: Access page within approved range (should succeed)
        response = self.client.get(url, {"page_range": "3"})
        assert response.status_code == status.HTTP_200_OK
        assert response["Content-Type"] == "application/pdf"

        # Test 2: Access range within approved range (should succeed)
        response = self.client.get(url, {"page_range": "2-3"})
        assert response.status_code == status.HTTP_200_OK
        assert response["Content-Type"] == "application/pdf"

        # Test 3: Access page outside approved range (should fail)
        response = self.client.get(url, {"page_range": "5"})
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "not authorized" in response.content.decode().lower()

    def test_invalid_page_range_returns_helpful_error(self) -> None:
        """
        Test that invalid page ranges return helpful error messages with valid range.

        This ensures users get clear feedback when they request pages that don't exist.
        """
        # Enable pagination for the file (has 5 pages)
        self.file.requires_pagination = True
        self.file.save()

        self.client.force_authenticate(user=self.instructor)
        url = reverse(
            "file-view",
            kwargs={"patient_pk": self.patient.id, "pk": self.file.id},
        )

        # Test 1: Request page beyond PDF total pages
        response = self.client.get(url, {"page_range": "10"})
        assert response.status_code == status.HTTP_403_FORBIDDEN
        response_text = response.content.decode()
        assert "invalid page range" in response_text.lower()
        assert "valid pages: 1-5" in response_text.lower()

        # Test 2: Request range with some invalid pages
        response = self.client.get(url, {"page_range": "4-10"})
        assert response.status_code == status.HTTP_403_FORBIDDEN
        response_text = response.content.decode()
        assert "invalid page range" in response_text.lower()
        assert "valid pages: 1-5" in response_text.lower()

        # Test 3: Request page 0 (invalid)
        response = self.client.get(url, {"page_range": "0"})
        assert response.status_code == status.HTTP_403_FORBIDDEN
        response_text = response.content.decode()
        assert "invalid page range" in response_text.lower()

    def test_student_invalid_page_shows_both_errors(self) -> None:
        """
        Test that students get appropriate error for invalid pages.

        When a student requests an invalid page, they should get an error
        about the page being invalid (not about authorization).
        """
        # Enable pagination for the file (has 5 pages)
        self.file.requires_pagination = True
        self.file.save()

        self.client.force_authenticate(user=self.student)
        url = reverse(
            "file-view",
            kwargs={"patient_pk": self.patient.id, "pk": self.file.id},
        )

        # Student approved range is "1-3"
        # Test: Request page beyond PDF total pages (page 10)
        response = self.client.get(url, {"page_range": "10"})
        assert response.status_code == status.HTTP_403_FORBIDDEN
        response_text = response.content.decode()
        # Should see error about invalid page range, not authorization
        assert "invalid page range" in response_text.lower()
        assert "valid pages: 1-5" in response_text.lower()

    def test_student_multiple_approved_files_merge_page_ranges(self) -> None:
        """Test that multiple approved files for same file merge page ranges"""
        from student_groups.models import BloodTestRequest

        # Enable pagination for the file (has 5 pages)
        self.file.requires_pagination = True
        self.file.save()

        # Delete the default approved file and create specific ones for testing
        ApprovedFile.objects.filter(file=self.file).delete()

        # Create approved files with non-overlapping ranges to test merging
        # First approved file: "1-2" (from imaging request)
        ApprovedFile.objects.create(
            imaging_request=self.imaging_request,
            file=self.file,
            page_range="1-2",
        )

        # Second approved file: "4" (from blood test request)
        blood_test_request = BloodTestRequest.objects.create(
            user=self.student,
            patient=self.patient,
            test_types=["FBC"],
            details="Test details",
            name="Dr. Lab",
            role="Pathologist",
            status="completed",
        )
        ApprovedFile.objects.create(
            blood_test_request=blood_test_request,
            file=self.file,
            page_range="4",
        )

        # Third approved file: "5" (from another imaging request)
        imaging_request2 = ImagingRequest.objects.create(
            user=self.student,
            patient=self.patient,
            test_type=ImagingRequest.TestType.ULTRASOUND_SCAN,
            details="Second imaging request for file integration test",
            infection_control_precautions=ImagingRequest.InfectionControlPrecaution.NONE,
            imaging_focus="Abdomen",
            name="Dr. Test",
            role="Doctor",
            status="completed",
        )
        ApprovedFile.objects.create(
            imaging_request=imaging_request2,
            file=self.file,
            page_range="5",
        )

        self.client.force_authenticate(user=self.student)
        url = reverse(
            "file-view",
            kwargs={"patient_pk": self.patient.id, "pk": self.file.id},
        )

        # Merged page range should be "1-2,4-5" (page 3 is not authorized)

        # Test: Student should be able to access page 1 (from first approved file)
        response = self.client.get(url, {"page_range": "1"})
        assert response.status_code == status.HTTP_200_OK
        assert response["Content-Type"] == "application/pdf"

        # Test: Student should be able to access page 2 (from first approved file)
        response = self.client.get(url, {"page_range": "2"})
        assert response.status_code == status.HTTP_200_OK
        assert response["Content-Type"] == "application/pdf"

        # Test: Student should be able to access page 4 (from second approved file)
        response = self.client.get(url, {"page_range": "4"})
        assert response.status_code == status.HTTP_200_OK
        assert response["Content-Type"] == "application/pdf"

        # Test: Student should be able to access page 5 (from third approved file)
        response = self.client.get(url, {"page_range": "5"})
        assert response.status_code == status.HTTP_200_OK
        assert response["Content-Type"] == "application/pdf"

        # Test: Student should NOT be able to access page 3 (not in any approved range)
        response = self.client.get(url, {"page_range": "3"})
        assert response.status_code == status.HTTP_403_FORBIDDEN
        response_text = response.content.decode()
        assert (
            "not authorized" in response_text.lower()
            or "unauthorized" in response_text.lower()
        )

        # Test: Student can access multiple pages from merged ranges
        response = self.client.get(url, {"page_range": "1,2,4,5"})
        assert response.status_code == status.HTTP_200_OK
        assert response["Content-Type"] == "application/pdf"

        # Test: Student cannot access mix of authorized and unauthorized pages
        response = self.client.get(url, {"page_range": "1,3"})
        assert response.status_code == status.HTTP_403_FORBIDDEN
