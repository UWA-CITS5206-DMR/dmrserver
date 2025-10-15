import shutil
import tempfile
from uuid import uuid4

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from core.context import Role
from student_groups.models import ApprovedFile, ImagingRequest

from .models import File, GoogleFormLink, Patient


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

        user = get_user_model().objects.create_user(
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

        suffix = uuid4().hex[:8]
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


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class PatientApiTests(APITestCase, RoleFixtureMixin):
    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()
        cls.instructor_group, created = Group.objects.get_or_create(
            name=Role.INSTRUCTOR.value,
        )
        cls.user = get_user_model().objects.create_user(
            username="tester",
            email="tester@example.com",
            password="pass1234",
        )
        cls.user.groups.add(cls.instructor_group)

    def setUp(self) -> None:
        self.client: APIClient = APIClient()
        self.media_root = settings.MEDIA_ROOT
        self.client.force_authenticate(user=self.user)

    def tearDown(self) -> None:
        pass

    @classmethod
    def tearDownClass(cls) -> None:
        try:
            from pathlib import Path

            if Path(settings.MEDIA_ROOT).is_dir():
                shutil.rmtree(settings.MEDIA_ROOT, ignore_errors=True)
        finally:
            super().tearDownClass()

    def _patient_payload(self, **overrides):
        payload = {
            "first_name": "John",
            "last_name": "Doe",
            "date_of_birth": "1990-01-01",
            "gender": Patient.Gender.MALE,
            "mrn": overrides.get("mrn", f"MRN-{uuid4().hex[:8]}"),
            "ward": overrides.get("ward", "Ward A"),
            "bed": overrides.get("bed", "Bed 1"),
            "phone_number": "+1234567890",
        }
        # Allow callers to override defaults
        payload.update(overrides)
        return payload

    def create_patient(self, **overrides) -> Patient:
        return Patient.objects.create(**self._patient_payload(**overrides))

    def upload_file(self, patient: Patient, name: str = "report.txt") -> File:
        upload_url = reverse("patient-upload-file", args=[patient.id])
        test_content = b"dummy-content"
        upload = SimpleUploadedFile(name, test_content, content_type="text/plain")
        res_upload = self.client.post(
            upload_url,
            data={"file": upload},
            format="multipart",
        )
        assert res_upload.status_code == status.HTTP_201_CREATED
        return File.objects.get(patient=patient)

    def test_auth_required_for_list(self) -> None:
        self.client.force_authenticate(user=None)
        url = reverse("patient-list")
        res = self.client.get(url)
        assert res.status_code == status.HTTP_401_UNAUTHORIZED

    def test_create_patient(self) -> None:
        url = reverse("patient-list")
        res = self.client.post(url, data=self._patient_payload(), format="json")
        assert res.status_code == status.HTTP_201_CREATED
        assert Patient.objects.count() == 1
        patient = Patient.objects.first()
        assert patient.first_name == "John"
        assert patient.last_name == "Doe"
        assert patient.gender == Patient.Gender.MALE

    def test_list_and_retrieve_patient(self) -> None:
        p = Patient.objects.create(**self._patient_payload())
        list_url = reverse("patient-list")
        res_list = self.client.get(list_url)
        assert res_list.status_code == status.HTTP_200_OK
        assert res_list.data["count"] >= 1

        detail_url = reverse("patient-detail", args=[p.id])
        res_detail = self.client.get(detail_url)
        assert res_detail.status_code == status.HTTP_200_OK
        assert res_detail.data["id"] == p.id

    def test_update_patient(self) -> None:
        p = self.create_patient()
        detail_url = reverse("patient-detail", args=[p.id])
        update_payload = {"first_name": "Jane", "phone_number": "+1999999999"}
        res_patch = self.client.patch(detail_url, data=update_payload, format="json")
        assert res_patch.status_code == status.HTTP_200_OK
        p.refresh_from_db()
        assert p.first_name == "Jane"
        assert p.phone_number == "+1999999999"

    def test_delete_patient(self) -> None:
        p = self.create_patient()
        detail_url = reverse("patient-detail", args=[p.id])
        res_delete = self.client.delete(detail_url)
        assert res_delete.status_code == status.HTTP_204_NO_CONTENT
        assert Patient.objects.count() == 0

    def test_upload_file_action(self) -> None:
        p = self.create_patient()
        f = self.upload_file(p)
        assert File.objects.filter(patient=p).count() == 1
        assert f.display_name == "report.txt"

    def test_list_files_for_patient(self) -> None:
        p = self.create_patient()
        self.upload_file(p)
        files_list_url = reverse("file-list", kwargs={"patient_pk": p.id})
        res_files = self.client.get(files_list_url)
        assert res_files.status_code == status.HTTP_200_OK
        assert res_files.data["count"] == 1

    def test_retrieve_file_detail(self) -> None:
        p = self.create_patient()
        f = self.upload_file(p)
        file_detail_url = reverse(
            "file-detail",
            kwargs={"patient_pk": p.id, "pk": str(f.id)},
        )
        res_file_detail = self.client.get(file_detail_url)
        assert res_file_detail.status_code == status.HTTP_200_OK
        assert res_file_detail.data["id"] == str(f.id)

    def test_delete_file_for_patient(self) -> None:
        p = self.create_patient()
        f = self.upload_file(p)
        file_detail_url = reverse(
            "file-detail",
            kwargs={"patient_pk": p.id, "pk": str(f.id)},
        )
        res_delete = self.client.delete(file_detail_url)
        assert res_delete.status_code == status.HTTP_204_NO_CONTENT
        assert File.objects.filter(patient=p).count() == 0

    def test_file_display_name_auto_generated_on_save(self) -> None:
        """
        Test that display_name is automatically extracted from filename when creating File objects directly
        (e.g., through Admin). This test simulates Django Admin behavior without using serializers.
        """
        p = self.create_patient()
        test_content = b"test content for display name"
        uploaded_file = SimpleUploadedFile(
            "test_document.pdf",
            test_content,
            content_type="application/pdf",
        )

        # Create File object directly without using API (simulating Admin save)
        file_obj = File.objects.create(
            patient=p,
            file=uploaded_file,
            category=File.Category.PATHOLOGY,
            requires_pagination=False,
        )

        # Verify display_name is automatically set to the uploaded filename
        assert file_obj.display_name == "test_document.pdf"
        assert file_obj.display_name is not None
        assert file_obj.display_name != ""

    def test_file_display_name_not_overwritten_if_set(self) -> None:
        """
        Test that the save() method does not overwrite display_name if it's already set.
        """
        p = self.create_patient()
        test_content = b"test content"
        uploaded_file = SimpleUploadedFile(
            "original.txt",
            test_content,
            content_type="text/plain",
        )

        # Create File object directly and set custom display_name
        file_obj = File(
            patient=p,
            file=uploaded_file,
            display_name="Custom Display Name",
            category=File.Category.OTHER,
        )
        file_obj.save()

        # Verify display_name remains as the custom value
        assert file_obj.display_name == "Custom Display Name"


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class FileManagementTestCase(APITestCase):
    """
    Unit tests for file management operations focusing on:
    - requires_pagination field
    - Permission enforcement for instructors/admins/students
    - File category handling
    - File CRUD operations
    """

    @classmethod
    def setUpTestData(cls) -> None:
        """Set up test users with different roles."""
        # Create groups
        cls.admin_group = Group.objects.get_or_create(name=Role.ADMIN.value)[0]
        cls.instructor_group = Group.objects.get_or_create(name=Role.INSTRUCTOR.value)[
            0
        ]
        cls.student_group = Group.objects.get_or_create(name=Role.STUDENT.value)[0]

        # Create admin user
        cls.admin_user = get_user_model().objects.create_user(
            username="admin_user",
            email="admin@example.com",
            password="admin123",
            is_superuser=True,
        )

        # Create instructor user
        cls.instructor_user = get_user_model().objects.create_user(
            username="instructor_user",
            email="instructor@example.com",
            password="instructor123",
        )
        cls.instructor_user.groups.add(cls.instructor_group)

        # Create student user
        cls.student_user = get_user_model().objects.create_user(
            username="student_user",
            email="student@example.com",
            password="student123",
        )
        cls.student_user.groups.add(cls.student_group)

        # Create a test patient
        cls.patient = Patient.objects.create(
            first_name="Test",
            last_name="Patient",
            date_of_birth="1990-01-01",
            gender=Patient.Gender.FEMALE,
            mrn="MRN_PATIENTS_001",
            ward="Ward Patients",
            bed="Bed 1",
            phone_number="+1234567890",
        )

        # Pre-generate a small PDF to reuse in tests and avoid repeated PyPDF2 generation
        try:
            from tests.test_utils import create_test_pdf

            cls._cached_pdf = create_test_pdf(num_pages=1)
        except Exception:  # noqa: BLE001 - fallback to allow test suite to proceed without fixture
            cls._cached_pdf = None

    def setUp(self) -> None:
        """Set up test client for each test."""
        self.client: APIClient = APIClient()
        self.media_root = settings.MEDIA_ROOT

    @classmethod
    def tearDownClass(cls) -> None:
        """Clean up media files after all tests."""
        try:
            from pathlib import Path

            if Path(settings.MEDIA_ROOT).is_dir():
                shutil.rmtree(settings.MEDIA_ROOT, ignore_errors=True)
        finally:
            super().tearDownClass()

    def _create_test_pdf(self, filename="test.pdf"):
        """Create a valid test PDF file using PyPDF2."""
        # Reuse cached PDF bytes when available
        cached = getattr(self.__class__, "_cached_pdf", None)
        if cached is not None:
            return SimpleUploadedFile(filename, cached, content_type="application/pdf")

        from tests.test_utils import create_test_pdf

        pdf_content = create_test_pdf(num_pages=1)
        return SimpleUploadedFile(filename, pdf_content, content_type="application/pdf")

    def _create_test_txt(self, filename="test.txt", content=b"Test content"):
        """Create a simple test text file."""
        return SimpleUploadedFile(filename, content, content_type="text/plain")

    def _get_file_list_url(self):
        """Get URL for file list endpoint."""
        return reverse("file-list", kwargs={"patient_pk": self.patient.id})

    def _get_file_detail_url(self, file_id):
        """Get URL for file detail endpoint."""
        return reverse(
            "file-detail",
            kwargs={"patient_pk": self.patient.id, "pk": str(file_id)},
        )

    # ==================== Permission Tests ====================

    def test_instructor_can_upload_file(self) -> None:
        """Test that instructor can upload files."""
        self.client.force_authenticate(user=self.instructor_user)
        url = self._get_file_list_url()

        pdf_file = self._create_test_pdf()
        data = {
            "file": pdf_file,
            "category": File.Category.IMAGING,
            "requires_pagination": False,
        }

        response = self.client.post(url, data, format="multipart")
        assert response.status_code == status.HTTP_201_CREATED
        assert File.objects.count() == 1

    def test_admin_can_upload_file(self) -> None:
        """Test that admin can upload files."""
        self.client.force_authenticate(user=self.admin_user)
        url = self._get_file_list_url()

        pdf_file = self._create_test_pdf()
        data = {
            "file": pdf_file,
            "category": File.Category.PATHOLOGY,
            "requires_pagination": False,
        }

        response = self.client.post(url, data, format="multipart")
        assert response.status_code == status.HTTP_201_CREATED

    def test_student_cannot_upload_file(self) -> None:
        """Test that student cannot upload files."""
        self.client.force_authenticate(user=self.student_user)
        url = self._get_file_list_url()

        pdf_file = self._create_test_pdf()
        data = {
            "file": pdf_file,
            "category": File.Category.IMAGING,
            "requires_pagination": False,
        }

        response = self.client.post(url, data, format="multipart")
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert File.objects.count() == 0

    def test_unauthenticated_cannot_upload_file(self) -> None:
        """Test that unauthenticated users cannot upload files."""
        url = self._get_file_list_url()

        pdf_file = self._create_test_pdf()
        data = {
            "file": pdf_file,
            "category": File.Category.IMAGING,
        }

        response = self.client.post(url, data, format="multipart")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_instructor_can_delete_file(self) -> None:
        """Test that instructor can delete files."""
        self.client.force_authenticate(user=self.instructor_user)

        # Create a file first
        file_obj = File.objects.create(
            patient=self.patient,
            file=self._create_test_pdf(),
            display_name="test.pdf",
            category=File.Category.IMAGING,
        )

        url = self._get_file_detail_url(file_obj.id)
        response = self.client.delete(url)
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert File.objects.count() == 0

    def test_student_cannot_delete_file(self) -> None:
        """Test that student cannot delete files."""
        self.client.force_authenticate(user=self.student_user)

        # Create a file first
        file_obj = File.objects.create(
            patient=self.patient,
            file=self._create_test_pdf(),
            display_name="test.pdf",
            category=File.Category.IMAGING,
        )

        url = self._get_file_detail_url(file_obj.id)
        response = self.client.delete(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert File.objects.count() == 1

    def test_instructor_can_update_file_metadata(self) -> None:
        """Test that instructor can update file metadata."""
        self.client.force_authenticate(user=self.instructor_user)

        # Create a file first
        file_obj = File.objects.create(
            patient=self.patient,
            file=self._create_test_pdf(),
            display_name="test.pdf",
            category=File.Category.IMAGING,
            requires_pagination=False,
        )

        url = self._get_file_detail_url(file_obj.id)
        data = {
            "category": File.Category.PATHOLOGY,
            "requires_pagination": True,
        }

        response = self.client.patch(url, data, format="json")
        assert response.status_code == status.HTTP_200_OK

        file_obj.refresh_from_db()
        assert file_obj.category == File.Category.PATHOLOGY
        assert file_obj.requires_pagination

    def test_student_cannot_update_file(self) -> None:
        """Test that student cannot update file metadata."""
        self.client.force_authenticate(user=self.student_user)

        # Create a file first
        file_obj = File.objects.create(
            patient=self.patient,
            file=self._create_test_pdf(),
            display_name="test.pdf",
            category=File.Category.IMAGING,
        )

        url = self._get_file_detail_url(file_obj.id)
        data = {"category": File.Category.PATHOLOGY}

        response = self.client.patch(url, data, format="json")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    # ==================== requires_pagination Field Tests ====================

    def test_upload_pdf_with_pagination_enabled(self) -> None:
        """Test uploading a PDF with requires_pagination=True."""
        self.client.force_authenticate(user=self.instructor_user)
        url = self._get_file_list_url()

        pdf_file = self._create_test_pdf("paginated.pdf")
        data = {
            "file": pdf_file,
            "category": File.Category.IMAGING,
            "requires_pagination": True,
        }

        response = self.client.post(url, data, format="multipart")
        assert response.status_code == status.HTTP_201_CREATED

        file_obj = File.objects.first()
        assert file_obj.requires_pagination
        assert file_obj.category == File.Category.IMAGING

    def test_upload_non_pdf_with_pagination_fails(self) -> None:
        """Test that non-PDF files cannot have requires_pagination=True."""
        self.client.force_authenticate(user=self.instructor_user)
        url = self._get_file_list_url()

        txt_file = self._create_test_txt("document.txt")
        data = {
            "file": txt_file,
            "category": File.Category.OTHER,
            "requires_pagination": True,
        }

        response = self.client.post(url, data, format="multipart")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "requires_pagination" in response.data
        assert File.objects.count() == 0

    def test_upload_pdf_without_pagination(self) -> None:
        """Test uploading a PDF with requires_pagination=False."""
        self.client.force_authenticate(user=self.instructor_user)
        url = self._get_file_list_url()

        pdf_file = self._create_test_pdf("non_paginated.pdf")
        data = {
            "file": pdf_file,
            "category": File.Category.PATHOLOGY,
            "requires_pagination": False,
        }

        response = self.client.post(url, data, format="multipart")
        assert response.status_code == status.HTTP_201_CREATED

        file_obj = File.objects.first()
        assert not file_obj.requires_pagination

    def test_update_pagination_to_true_for_pdf(self) -> None:
        """Test updating requires_pagination to True for an existing PDF."""
        self.client.force_authenticate(user=self.instructor_user)

        # Create PDF file with pagination disabled
        file_obj = File.objects.create(
            patient=self.patient,
            file=self._create_test_pdf(),
            display_name="test.pdf",
            category=File.Category.IMAGING,
            requires_pagination=False,
        )

        url = self._get_file_detail_url(file_obj.id)
        data = {"requires_pagination": True}

        response = self.client.patch(url, data, format="json")
        assert response.status_code == status.HTTP_200_OK

        file_obj.refresh_from_db()
        assert file_obj.requires_pagination

    # ==================== Category Tests ====================

    def test_upload_file_with_different_categories(self) -> None:
        """Test uploading files with different category values."""
        self.client.force_authenticate(user=self.instructor_user)
        url = self._get_file_list_url()

        categories = [
            File.Category.ADMISSION,
            File.Category.PATHOLOGY,
            File.Category.IMAGING,
            File.Category.DIAGNOSTICS,
            File.Category.LAB_RESULTS,
            File.Category.OTHER,
        ]

        for i, category in enumerate(categories):
            pdf_file = self._create_test_pdf(f"test_{i}.pdf")
            data = {
                "file": pdf_file,
                "category": category,
                "requires_pagination": False,
            }

            response = self.client.post(url, data, format="multipart")
            assert response.status_code == status.HTTP_201_CREATED
            assert response.data["category"] == category

        assert File.objects.count() == len(categories)

    def test_default_category_is_other(self) -> None:
        """Test that default category is OTHER when not specified."""
        self.client.force_authenticate(user=self.instructor_user)
        url = self._get_file_list_url()

        pdf_file = self._create_test_pdf()
        data = {"file": pdf_file}

        response = self.client.post(url, data, format="multipart")
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["category"] == File.Category.OTHER

    # ==================== Display Name Tests ====================

    def test_file_upload_display_name_auto_generated(self) -> None:
        """Test that display_name is automatically generated from filename."""
        self.client.force_authenticate(user=self.instructor_user)
        url = self._get_file_list_url()

        pdf_file = self._create_test_pdf("my_report.pdf")
        data = {
            "file": pdf_file,
            "category": File.Category.PATHOLOGY,
        }

        response = self.client.post(url, data, format="multipart")
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["display_name"] == "my_report.pdf"

    # ==================== List and Retrieve Tests ====================

    def test_instructor_can_list_files(self) -> None:
        """Test that instructor can list all files for a patient."""
        self.client.force_authenticate(user=self.instructor_user)

        # Create multiple files
        for i in range(3):
            File.objects.create(
                patient=self.patient,
                file=self._create_test_pdf(f"test_{i}.pdf"),
                display_name=f"test_{i}.pdf",
                category=File.Category.IMAGING,
            )

        url = self._get_file_list_url()
        response = self.client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 3

    def test_instructor_can_retrieve_file_details(self) -> None:
        """Test that instructor can retrieve file details."""
        self.client.force_authenticate(user=self.instructor_user)

        file_obj = File.objects.create(
            patient=self.patient,
            file=self._create_test_pdf(),
            display_name="test.pdf",
            category=File.Category.PATHOLOGY,
            requires_pagination=True,
        )

        url = self._get_file_detail_url(file_obj.id)
        response = self.client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["id"] == str(file_obj.id)
        assert response.data["category"] == File.Category.PATHOLOGY
        assert response.data["requires_pagination"]

    def test_student_can_list_files_with_filtering(self) -> None:
        """Test that student can list files but only sees Admission files and approved files."""
        self.client.force_authenticate(user=self.student_user)

        # Create an Admission file - should be visible to student
        admission_file = File.objects.create(
            patient=self.patient,
            file=self._create_test_pdf(),
            display_name="admission.pdf",
            category=File.Category.ADMISSION,
        )

        # Create an Imaging file - should NOT be visible to student (no approval)
        imaging_file = File.objects.create(
            patient=self.patient,
            file=self._create_test_pdf(),
            display_name="imaging.pdf",
            category=File.Category.IMAGING,
        )

        url = self._get_file_list_url()
        response = self.client.get(url)

        # Student should be able to list files
        assert response.status_code == status.HTTP_200_OK

        # Response should contain results
        assert "results" in response.data
        file_ids = [f["id"] for f in response.data["results"]]

        # Should see Admission file
        assert str(admission_file.id) in file_ids

        # Should NOT see Imaging file (not approved)
        assert str(imaging_file.id) not in file_ids

    def test_student_can_see_approved_files_from_completed_requests(self) -> None:
        """Test that student can see files approved in their completed lab requests."""
        self.client.force_authenticate(user=self.student_user)

        # Create a Pathology file - not Admission, so normally not visible
        pathology_file = File.objects.create(
            patient=self.patient,
            file=self._create_test_pdf(),
            display_name="pathology.pdf",
            category=File.Category.PATHOLOGY,
        )

        # Create another file that won't be approved
        imaging_file = File.objects.create(
            patient=self.patient,
            file=self._create_test_pdf(),
            display_name="imaging.pdf",
            category=File.Category.IMAGING,
        )

        # Create a completed imaging request for this student
        imaging_request = ImagingRequest.objects.create(
            patient=self.patient,
            user=self.student_user,
            test_type=ImagingRequest.TestType.X_RAY,
            details="Test imaging request",
            infection_control_precautions=ImagingRequest.InfectionControlPrecaution.NONE,
            imaging_focus="Chest",
            status="completed",  # Important: must be completed
            name="Test Student",
            role="Student",
        )

        # Approve the pathology file for this request
        ApprovedFile.objects.create(
            imaging_request=imaging_request,
            file=pathology_file,
            page_range="1-5",
        )

        url = self._get_file_list_url()
        response = self.client.get(url)

        # Student should be able to list files
        assert response.status_code == status.HTTP_200_OK

        # Response should contain results
        assert "results" in response.data
        file_ids = [f["id"] for f in response.data["results"]]

        # Should see the approved pathology file
        assert str(pathology_file.id) in file_ids

        # Should NOT see the imaging file (not approved)
        assert str(imaging_file.id) not in file_ids

    def test_student_cannot_see_approved_files_from_pending_requests(self) -> None:
        """Test that student cannot see files from pending (not completed) lab requests."""
        self.client.force_authenticate(user=self.student_user)

        # Create a Pathology file
        pathology_file = File.objects.create(
            patient=self.patient,
            file=self._create_test_pdf(),
            display_name="pathology.pdf",
            category=File.Category.PATHOLOGY,
        )

        # Create a PENDING imaging request (not completed)
        imaging_request = ImagingRequest.objects.create(
            patient=self.patient,
            user=self.student_user,
            test_type=ImagingRequest.TestType.X_RAY,
            details="Test imaging request",
            infection_control_precautions=ImagingRequest.InfectionControlPrecaution.NONE,
            imaging_focus="Chest",
            status="pending",  # Important: pending, not completed
            name="Test Student",
            role="Student",
        )

        # "Approve" the file for this pending request
        ApprovedFile.objects.create(
            imaging_request=imaging_request,
            file=pathology_file,
            page_range="1-5",
        )

        url = self._get_file_list_url()
        response = self.client.get(url)

        # Student should be able to list files
        assert response.status_code == status.HTTP_200_OK

        # Response should contain results
        assert "results" in response.data
        file_ids = [f["id"] for f in response.data["results"]]

        # Should NOT see the file because request is not completed
        assert str(pathology_file.id) not in file_ids


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class FileUploadMultipartParserTests(APITestCase):
    """
    Test file upload functionality with multipart/form-data parser.

    These tests verify that the MultiPartParser is properly configured
    to handle binary file content (including non-UTF-8 bytes) without
    attempting to decode them as UTF-8 JSON.

    Related Issue: Fixed JSON parse error when uploading PDF files
    with binary content containing bytes like 0xe2.
    """

    @classmethod
    def setUpTestData(cls) -> None:
        """Set up test data for all tests in this class."""
        cls.instructor_group, _ = Group.objects.get_or_create(
            name=Role.INSTRUCTOR.value,
        )
        cls.instructor_user = get_user_model().objects.create_user(
            username="test_instructor",
            email="instructor@test.com",
            password="testpass123",
        )
        cls.instructor_user.groups.add(cls.instructor_group)

    def setUp(self) -> None:
        """Set up test fixtures for each test method."""
        self.client = APIClient()
        self.client.force_authenticate(user=self.instructor_user)
        self.media_root = settings.MEDIA_ROOT

        # Create test patient
        self.patient = Patient.objects.create(
            first_name="Test",
            last_name="Patient",
            date_of_birth="1990-01-01",
            mrn="MRN_PATIENTS_002",
            ward="Ward Patients",
            bed="Bed 2",
        )

    @classmethod
    def tearDownClass(cls) -> None:
        """Clean up after all tests in this class."""
        try:
            from pathlib import Path

            if Path(settings.MEDIA_ROOT).is_dir():
                shutil.rmtree(settings.MEDIA_ROOT, ignore_errors=True)
        finally:
            super().tearDownClass()

    def _create_pdf_with_binary_content(self, filename="test.pdf"):
        """
        Create a valid PDF file with binary content using PyPDF2.

        This creates a proper PDF with correct xref table structure to avoid
        "incorrect startxref pointer" warnings. The PDF includes proper
        structure to simulate real PDF files.
        """
        from tests.test_utils import create_test_pdf

        # Create a valid PDF with proper structure
        pdf_content = create_test_pdf(num_pages=1)

        return SimpleUploadedFile(
            name=filename,
            content=pdf_content,
            content_type="application/pdf",
        )

    def test_upload_pdf_with_binary_content(self) -> None:
        """
        Test uploading a PDF file with binary content via multipart/form-data.

        This test verifies that:
        1. Binary PDF content with non-UTF-8 bytes is properly handled
        2. MultiPartParser correctly parses the multipart request
        3. No UTF-8 decode errors occur
        4. File is saved correctly to disk
        5. Database record is created with correct metadata
        """
        url = reverse("file-list", kwargs={"patient_pk": self.patient.id})

        pdf_file = self._create_pdf_with_binary_content(
            "Admission Proforma Toni Baxter.pdf",
        )
        data = {
            "file": pdf_file,
            "category": File.Category.ADMISSION,
            "requires_pagination": False,
        }

        response = self.client.post(url, data, format="multipart")

        # Verify successful upload
        assert response.status_code == status.HTTP_201_CREATED
        assert "id" in response.data
        assert response.data["category"] == File.Category.ADMISSION
        assert not response.data["requires_pagination"]
        assert response.data["display_name"] == "Admission Proforma Toni Baxter.pdf"

        # Verify file was created in database
        file_obj = File.objects.get(id=response.data["id"])
        assert file_obj.patient == self.patient
        assert file_obj.category == File.Category.ADMISSION
        assert not file_obj.requires_pagination

    # file existence checks are performed inside test methods where `file_obj` is in scope

    def test_upload_pdf_with_binary_content_and_pagination(self) -> None:
        """
        Test uploading a PDF with binary content and requires_pagination=True.

        This ensures that the multipart parser works correctly with both
        binary file data and boolean form fields.
        """
        url = reverse("file-list", kwargs={"patient_pk": self.patient.id})

        pdf_file = self._create_pdf_with_binary_content("imaging_report.pdf")
        data = {
            "file": pdf_file,
            "category": File.Category.IMAGING,
            "requires_pagination": True,
        }

        response = self.client.post(url, data, format="multipart")

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["requires_pagination"]
        assert response.data["category"] == File.Category.IMAGING

        file_obj = File.objects.get(id=response.data["id"])
        assert file_obj.requires_pagination

    def test_upload_multiple_pdfs_with_binary_content(self) -> None:
        """
        Test uploading multiple PDF files with binary content sequentially.

        This verifies that the parser configuration works consistently
        across multiple requests.
        """
        url = reverse("file-list", kwargs={"patient_pk": self.patient.id})

        categories = [
            File.Category.ADMISSION,
            File.Category.PATHOLOGY,
            File.Category.IMAGING,
        ]

        for i, category in enumerate(categories):
            pdf_file = self._create_pdf_with_binary_content(f"test_{i}.pdf")
            data = {
                "file": pdf_file,
                "category": category,
                "requires_pagination": False,
            }

            response = self.client.post(url, data, format="multipart")

            assert response.status_code == status.HTTP_201_CREATED
            assert response.data["category"] == category

        # Verify all files were created
        assert File.objects.filter(patient=self.patient).count() == 3

    def test_upload_pdf_via_legacy_endpoint(self) -> None:
        """
        Test uploading PDF with binary content via legacy upload_file endpoint.

        This ensures the legacy PatientViewSet.upload_file action also works
        with the multipart parser configuration.
        """
        url = reverse("patient-upload-file", args=[self.patient.id])

        pdf_file = self._create_pdf_with_binary_content("legacy_upload.pdf")
        data = {
            "file": pdf_file,
            "category": File.Category.LAB_RESULTS,
            "requires_pagination": False,
        }

        response = self.client.post(url, data, format="multipart")

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["category"] == File.Category.LAB_RESULTS

        # Verify file was created
        file_obj = File.objects.filter(patient=self.patient).first()
        assert file_obj is not None
        assert file_obj.display_name == "legacy_upload.pdf"

    def test_multipart_parser_with_mixed_content_types(self) -> None:
        """
        Test that multipart parser correctly handles requests with mixed content.

        This test verifies that the parser can handle both:
        - Binary file data (PDF with non-UTF-8 bytes)
        - Text form fields (category, requires_pagination)
        """
        url = reverse("file-list", kwargs={"patient_pk": self.patient.id})

        # Create a valid PDF for testing mixed content handling
        from tests.test_utils import create_test_pdf

        pdf_content = create_test_pdf(num_pages=1)

        pdf_file = SimpleUploadedFile(
            name="mixed_content.pdf",
            content=pdf_content,
            content_type="application/pdf",
        )

        data = {
            "file": pdf_file,
            "category": File.Category.DIAGNOSTICS,
            "requires_pagination": True,
        }

        response = self.client.post(url, data, format="multipart")

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["category"] == File.Category.DIAGNOSTICS
        assert response.data["requires_pagination"]

    def test_parser_preserves_binary_file_integrity(self) -> None:
        """
        Test that binary file content is preserved during upload.

        This verifies that the multipart parser does not corrupt or alter
        the binary content of uploaded files.
        """
        url = reverse("file-list", kwargs={"patient_pk": self.patient.id})

        # Create a valid PDF for testing file integrity
        from tests.test_utils import create_test_pdf

        original_content = create_test_pdf(num_pages=1)
        pdf_file = SimpleUploadedFile(
            name="integrity_test.pdf",
            content=original_content,
            content_type="application/pdf",
        )

        data = {
            "file": pdf_file,
            "category": File.Category.OTHER,
        }

        response = self.client.post(url, data, format="multipart")
        assert response.status_code == status.HTTP_201_CREATED

        # Read the saved file and verify content matches
        file_obj = File.objects.get(id=response.data["id"])
        from pathlib import Path

        with Path(file_obj.file.path).open("rb") as f:
            saved_content = f.read()

        assert saved_content == original_content


class GoogleFormLinkApiTests(APITestCase):
    """Test cases for GoogleFormLink API endpoints."""

    @classmethod
    def setUpTestData(cls) -> None:
        cls.instructor_group, created = Group.objects.get_or_create(
            name=Role.INSTRUCTOR.value,
        )
        cls.student_group, created = Group.objects.get_or_create(
            name=Role.STUDENT.value,
        )
        cls.instructor_user = get_user_model().objects.create_user(
            username="instructor",
            email="instructor@example.com",
            password="pass1234",
        )
        cls.instructor_user.groups.add(cls.instructor_group)

        cls.student_user = get_user_model().objects.create_user(
            username="student",
            email="student@example.com",
            password="pass1234",
        )
        cls.student_user.groups.add(cls.student_group)

    def setUp(self) -> None:
        # Create test Google Form links
        self.form1 = GoogleFormLink.objects.create(
            title="Patient Feedback Form",
            url="https://forms.google.com/feedback",
            description="Please provide your feedback",
            display_order=1,
            is_active=True,
        )
        self.form2 = GoogleFormLink.objects.create(
            title="Health Survey",
            url="https://forms.google.com/health-survey",
            description="Complete this health survey",
            display_order=2,
            is_active=True,
        )
        self.inactive_form = GoogleFormLink.objects.create(
            title="Inactive Form",
            url="https://forms.google.com/inactive",
            description="This form is inactive",
            display_order=3,
            is_active=False,
        )

    def test_list_google_forms(self) -> None:
        """Test listing Google Form links for instructor (shows all forms)."""
        self.client.force_authenticate(user=self.instructor_user)
        url = reverse("google-form-list")
        response = self.client.get(url)

        assert response.status_code == status.HTTP_200_OK
        # Instructor should see all forms (active and inactive)
        assert len(response.data) == 3
        assert response.data[0]["title"] == "Patient Feedback Form"
        assert response.data[1]["title"] == "Health Survey"
        assert response.data[2]["title"] == "Inactive Form"

    def test_list_google_forms_ordered_by_display_order(self) -> None:
        """Test that Google Forms are ordered by display_order."""
        self.client.force_authenticate(user=self.instructor_user)
        url = reverse("google-form-list")
        response = self.client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data[0]["display_order"] == 1
        assert response.data[1]["display_order"] == 2
        assert response.data[2]["display_order"] == 3

    def test_retrieve_google_form(self) -> None:
        """Test retrieving a specific Google Form link."""
        self.client.force_authenticate(user=self.instructor_user)
        url = reverse("google-form-detail", args=[self.form1.id])
        response = self.client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["title"] == "Patient Feedback Form"
        assert response.data["url"] == "https://forms.google.com/feedback"
        assert response.data["description"] == "Please provide your feedback"
        assert response.data["is_active"] is True

    def test_list_includes_all_forms_for_instructor(self) -> None:
        """Test that instructors can see all forms (active and inactive)."""
        self.client.force_authenticate(user=self.instructor_user)
        url = reverse("google-form-list")
        response = self.client.get(url)

        assert response.status_code == status.HTTP_200_OK
        # Verify all forms are included
        form_titles = [form["title"] for form in response.data]
        assert "Patient Feedback Form" in form_titles
        assert "Health Survey" in form_titles
        assert "Inactive Form" in form_titles

    def test_instructor_can_create_google_form(self) -> None:
        """Test that instructors can create new Google Form links."""
        self.client.force_authenticate(user=self.instructor_user)
        url = reverse("google-form-list")
        data = {
            "title": "New Form",
            "url": "https://forms.google.com/new",
            "description": "New form description",
            "display_order": 10,
            "is_active": True,
        }
        response = self.client.post(url, data, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["title"] == "New Form"
        assert response.data["url"] == "https://forms.google.com/new"

    def test_instructor_can_update_google_form(self) -> None:
        """Test that instructors can update Google Form links."""
        self.client.force_authenticate(user=self.instructor_user)
        url = reverse("google-form-detail", args=[self.form1.id])
        data = {
            "title": "Updated Form",
            "url": "https://forms.google.com/updated",
            "description": "Updated description",
            "display_order": 5,
            "is_active": False,
        }
        response = self.client.put(url, data, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["title"] == "Updated Form"
        assert response.data["is_active"] is False

    def test_instructor_can_delete_google_form(self) -> None:
        """Test that instructors can delete Google Form links."""
        self.client.force_authenticate(user=self.instructor_user)
        url = reverse("google-form-detail", args=[self.form1.id])
        response = self.client.delete(url)
        assert response.status_code == status.HTTP_204_NO_CONTENT

        # Verify it's deleted
        response = self.client.get(url)
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_google_form_response_structure(self) -> None:
        """Test that Google Form response includes all expected fields."""
        self.client.force_authenticate(user=self.instructor_user)
        url = reverse("google-form-detail", args=[self.form1.id])
        response = self.client.get(url)

        assert response.status_code == status.HTTP_200_OK
        expected_fields = {
            "id",
            "title",
            "url",
            "description",
            "display_order",
            "is_active",
            "created_at",
            "updated_at",
        }
        assert set(response.data.keys()) == expected_fields

    def test_student_can_only_read_active_forms(self) -> None:
        """Test that students can only see active forms."""
        self.client.force_authenticate(user=self.student_user)
        url = reverse("google-form-list")
        response = self.client.get(url)

        assert response.status_code == status.HTTP_200_OK
        # Students should only see active forms
        assert len(response.data) == 2
        form_titles = [form["title"] for form in response.data]
        assert "Patient Feedback Form" in form_titles
        assert "Health Survey" in form_titles
        assert "Inactive Form" not in form_titles

    def test_student_cannot_create_google_form(self) -> None:
        """Test that students cannot create Google Form links."""
        self.client.force_authenticate(user=self.student_user)
        url = reverse("google-form-list")
        data = {
            "title": "New Form",
            "url": "https://forms.google.com/new",
            "description": "New form description",
            "display_order": 10,
            "is_active": True,
        }
        response = self.client.post(url, data, format="json")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_student_cannot_update_google_form(self) -> None:
        """Test that students cannot update Google Form links."""
        self.client.force_authenticate(user=self.student_user)
        url = reverse("google-form-detail", args=[self.form1.id])
        data = {
            "title": "Updated Form",
            "url": "https://forms.google.com/updated",
            "description": "Updated description",
            "display_order": 5,
            "is_active": False,
        }
        response = self.client.put(url, data, format="json")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_student_cannot_delete_google_form(self) -> None:
        """Test that students cannot delete Google Form links."""
        self.client.force_authenticate(user=self.student_user)
        url = reverse("google-form-detail", args=[self.form1.id])
        response = self.client.delete(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN


class FilePermissionsTest(RoleFixtureMixin, APITestCase):
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
        # Lightweight per-test mocks
        from unittest.mock import Mock

        self.mock_request = Mock()
        self.mock_view = Mock()

    def test_admin_can_access_file(self) -> None:
        """Test that an admin has full access to files."""
        from core.permissions import FileAccessPermission

        permission = FileAccessPermission()
        self.mock_request.user = self.admin_user
        self.mock_request.method = "GET"

        # Admin should have access
        assert permission.has_object_permission(
            self.mock_request, self.mock_view, self.file
        )

    def test_instructor_can_access_file(self) -> None:
        """Test that an instructor has full access to files."""
        from core.permissions import FileAccessPermission

        permission = FileAccessPermission()
        self.mock_request.user = self.instructor_user
        self.mock_request.method = "GET"

        # Instructor should have access
        assert permission.has_object_permission(
            self.mock_request, self.mock_view, self.file
        )

    def test_student_cannot_access_file_without_approval(self) -> None:
        """Test that a student cannot access a file without an approved request."""
        from core.permissions import FileAccessPermission

        permission = FileAccessPermission()
        self.mock_request.user = self.student_user
        self.mock_request.method = "GET"

        # Student should not have access without approval
        assert not permission.has_object_permission(
            self.mock_request, self.mock_view, self.file
        )

    def test_student_can_access_file_with_approval(self) -> None:
        """Test that a student can access a file if their request was approved."""
        from core.permissions import FileAccessPermission

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
        from core.permissions import FileAccessPermission

        permission = FileAccessPermission()
        self.mock_request.user = self.instructor_user

        for method in ["GET", "HEAD", "OPTIONS"]:
            self.mock_request.method = method
            assert permission.has_permission(self.mock_request, self.mock_view)

    def test_instructor_write_methods_denied_by_permission_class(self) -> None:
        """Instructor write operations require the view to allow them explicitly."""
        from core.permissions import FileAccessPermission

        permission = FileAccessPermission()
        self.mock_request.user = self.instructor_user

        for method in ["POST", "PUT", "PATCH", "DELETE"]:
            self.mock_request.method = method
            assert not permission.has_permission(self.mock_request, self.mock_view)

    def test_student_cannot_manage_files(self) -> None:
        """Test that a student cannot create, update, or delete files."""
        from core.permissions import FileAccessPermission

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
