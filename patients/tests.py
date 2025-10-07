from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase, APIClient
import tempfile
import os
import shutil
from core.context import Role

from .models import Patient, File


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class PatientApiTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.instructor_group, created = Group.objects.get_or_create(
            name=Role.INSTRUCTOR.value
        )
        cls.user = get_user_model().objects.create_user(
            username="tester", email="tester@example.com", password="pass1234"
        )
        cls.user.groups.add(cls.instructor_group)

    def setUp(self):
        self.client: APIClient = APIClient()
        self.media_root = settings.MEDIA_ROOT
        self.client.force_authenticate(user=self.user)

    def tearDown(self):
        pass

    @classmethod
    def tearDownClass(cls):
        try:
            if os.path.isdir(settings.MEDIA_ROOT):
                shutil.rmtree(settings.MEDIA_ROOT, ignore_errors=True)
        finally:
            super().tearDownClass()

    def _patient_payload(self, **overrides):
        payload = {
            "first_name": "John",
            "last_name": "Doe",
            "date_of_birth": "1990-01-01",
            "email": "john.doe@example.com",
            "phone_number": "+1234567890",
        }
        payload.update(overrides)
        return payload

    def create_patient(self, **overrides) -> Patient:
        return Patient.objects.create(**self._patient_payload(**overrides))

    def upload_file(self, patient: Patient, name: str = "report.txt") -> File:
        upload_url = reverse("patient-upload-file", args=[patient.id])
        test_content = b"dummy-content"
        upload = SimpleUploadedFile(name, test_content, content_type="text/plain")
        res_upload = self.client.post(
            upload_url, data={"file": upload}, format="multipart"
        )
        self.assertEqual(res_upload.status_code, status.HTTP_201_CREATED)
        return File.objects.get(patient=patient)

    def test_auth_required_for_list(self):
        self.client.force_authenticate(user=None)
        url = reverse("patient-list")
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_patient(self):
        url = reverse("patient-list")
        res = self.client.post(url, data=self._patient_payload(), format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Patient.objects.count(), 1)
        patient = Patient.objects.first()
        self.assertEqual(patient.first_name, "John")
        self.assertEqual(patient.last_name, "Doe")
        self.assertEqual(patient.email, "john.doe@example.com")

    def test_list_and_retrieve_patient(self):
        p = Patient.objects.create(**self._patient_payload())
        list_url = reverse("patient-list")
        res_list = self.client.get(list_url)
        self.assertEqual(res_list.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(res_list.data["count"], 1)

        detail_url = reverse("patient-detail", args=[p.id])
        res_detail = self.client.get(detail_url)
        self.assertEqual(res_detail.status_code, status.HTTP_200_OK)
        self.assertEqual(res_detail.data["id"], p.id)

    def test_update_patient(self):
        p = self.create_patient()
        detail_url = reverse("patient-detail", args=[p.id])
        update_payload = {"first_name": "Jane", "email": "jane.doe@example.com"}
        res_patch = self.client.patch(detail_url, data=update_payload, format="json")
        self.assertEqual(res_patch.status_code, status.HTTP_200_OK)
        p.refresh_from_db()
        self.assertEqual(p.first_name, "Jane")
        self.assertEqual(p.email, "jane.doe@example.com")

    def test_delete_patient(self):
        p = self.create_patient()
        detail_url = reverse("patient-detail", args=[p.id])
        res_delete = self.client.delete(detail_url)
        self.assertEqual(res_delete.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Patient.objects.count(), 0)

    def test_upload_file_action(self):
        p = self.create_patient()
        f = self.upload_file(p)
        self.assertEqual(File.objects.filter(patient=p).count(), 1)
        self.assertEqual(f.display_name, "report.txt")

    def test_list_files_for_patient(self):
        p = self.create_patient()
        self.upload_file(p)
        files_list_url = reverse("file-list", kwargs={"patient_pk": p.id})
        res_files = self.client.get(files_list_url)
        self.assertEqual(res_files.status_code, status.HTTP_200_OK)
        self.assertEqual(res_files.data["count"], 1)

    def test_retrieve_file_detail(self):
        p = self.create_patient()
        f = self.upload_file(p)
        file_detail_url = reverse(
            "file-detail", kwargs={"patient_pk": p.id, "pk": str(f.id)}
        )
        res_file_detail = self.client.get(file_detail_url)
        self.assertEqual(res_file_detail.status_code, status.HTTP_200_OK)
        self.assertEqual(res_file_detail.data["id"], str(f.id))

    def test_delete_file_for_patient(self):
        p = self.create_patient()
        f = self.upload_file(p)
        file_detail_url = reverse(
            "file-detail", kwargs={"patient_pk": p.id, "pk": str(f.id)}
        )
        res_delete = self.client.delete(file_detail_url)
        self.assertEqual(res_delete.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(File.objects.filter(patient=p).count(), 0)

    def test_file_display_name_auto_generated_on_save(self):
        """
        Test that display_name is automatically extracted from filename when creating File objects directly
        (e.g., through Admin). This test simulates Django Admin behavior without using serializers.
        """
        p = self.create_patient()
        test_content = b"test content for display name"
        uploaded_file = SimpleUploadedFile(
            "test_document.pdf", test_content, content_type="application/pdf"
        )

        # Create File object directly without using API (simulating Admin save)
        file_obj = File.objects.create(
            patient=p,
            file=uploaded_file,
            category=File.Category.PATHOLOGY,
            requires_pagination=False,
        )

        # Verify display_name is automatically set to the uploaded filename
        self.assertEqual(file_obj.display_name, "test_document.pdf")
        self.assertIsNotNone(file_obj.display_name)
        self.assertNotEqual(file_obj.display_name, "")

    def test_file_display_name_not_overwritten_if_set(self):
        """
        Test that the save() method does not overwrite display_name if it's already set.
        """
        p = self.create_patient()
        test_content = b"test content"
        uploaded_file = SimpleUploadedFile(
            "original.txt", test_content, content_type="text/plain"
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
        self.assertEqual(file_obj.display_name, "Custom Display Name")


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
    def setUpTestData(cls):
        """Set up test users with different roles."""
        # Create groups
        cls.admin_group = Group.objects.get_or_create(name=Role.ADMIN.value)[0]
        cls.instructor_group = Group.objects.get_or_create(name=Role.INSTRUCTOR.value)[0]
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
            email="patient@example.com",
            phone_number="+1234567890",
        )

    def setUp(self):
        """Set up test client for each test."""
        self.client: APIClient = APIClient()
        self.media_root = settings.MEDIA_ROOT

    @classmethod
    def tearDownClass(cls):
        """Clean up media files after all tests."""
        try:
            if os.path.isdir(settings.MEDIA_ROOT):
                shutil.rmtree(settings.MEDIA_ROOT, ignore_errors=True)
        finally:
            super().tearDownClass()

    def _create_test_pdf(self, filename="test.pdf"):
        """Create a simple test PDF file."""
        # Minimal PDF structure
        pdf_content = b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj 2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj 3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]>>endobj\nxref\n0 4\n0000000000 65535 f\n0000000009 00000 n\n0000000056 00000 n\n0000000115 00000 n\ntrailer<</Size 4/Root 1 0 R>>\nstartxref\n190\n%%EOF"
        return SimpleUploadedFile(filename, pdf_content, content_type="application/pdf")

    def _create_test_txt(self, filename="test.txt", content=b"Test content"):
        """Create a simple test text file."""
        return SimpleUploadedFile(filename, content, content_type="text/plain")

    def _get_file_list_url(self):
        """Get URL for file list endpoint."""
        return reverse("file-list", kwargs={"patient_pk": self.patient.id})

    def _get_file_detail_url(self, file_id):
        """Get URL for file detail endpoint."""
        return reverse("file-detail", kwargs={"patient_pk": self.patient.id, "pk": str(file_id)})

    # ==================== Permission Tests ====================

    def test_instructor_can_upload_file(self):
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
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(File.objects.count(), 1)

    def test_admin_can_upload_file(self):
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
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_student_cannot_upload_file(self):
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
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(File.objects.count(), 0)

    def test_unauthenticated_cannot_upload_file(self):
        """Test that unauthenticated users cannot upload files."""
        url = self._get_file_list_url()

        pdf_file = self._create_test_pdf()
        data = {
            "file": pdf_file,
            "category": File.Category.IMAGING,
        }

        response = self.client.post(url, data, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_instructor_can_delete_file(self):
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
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(File.objects.count(), 0)

    def test_student_cannot_delete_file(self):
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
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(File.objects.count(), 1)

    def test_instructor_can_update_file_metadata(self):
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
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        file_obj.refresh_from_db()
        self.assertEqual(file_obj.category, File.Category.PATHOLOGY)
        self.assertTrue(file_obj.requires_pagination)

    def test_student_cannot_update_file(self):
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
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # ==================== requires_pagination Field Tests ====================

    def test_upload_pdf_with_pagination_enabled(self):
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
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        file_obj = File.objects.first()
        self.assertTrue(file_obj.requires_pagination)
        self.assertEqual(file_obj.category, File.Category.IMAGING)

    def test_upload_non_pdf_with_pagination_fails(self):
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
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("requires_pagination", response.data)
        self.assertEqual(File.objects.count(), 0)

    def test_upload_pdf_without_pagination(self):
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
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        file_obj = File.objects.first()
        self.assertFalse(file_obj.requires_pagination)

    def test_update_pagination_to_true_for_pdf(self):
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
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        file_obj.refresh_from_db()
        self.assertTrue(file_obj.requires_pagination)

    # ==================== Category Tests ====================

    def test_upload_file_with_different_categories(self):
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
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            self.assertEqual(response.data["category"], category)

        self.assertEqual(File.objects.count(), len(categories))

    def test_default_category_is_other(self):
        """Test that default category is OTHER when not specified."""
        self.client.force_authenticate(user=self.instructor_user)
        url = self._get_file_list_url()

        pdf_file = self._create_test_pdf()
        data = {"file": pdf_file}

        response = self.client.post(url, data, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["category"], File.Category.OTHER)

    # ==================== Display Name Tests ====================

    def test_file_upload_display_name_auto_generated(self):
        """Test that display_name is automatically generated from filename."""
        self.client.force_authenticate(user=self.instructor_user)
        url = self._get_file_list_url()

        pdf_file = self._create_test_pdf("my_report.pdf")
        data = {
            "file": pdf_file,
            "category": File.Category.PATHOLOGY,
        }

        response = self.client.post(url, data, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["display_name"], "my_report.pdf")

    # ==================== List and Retrieve Tests ====================

    def test_instructor_can_list_files(self):
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
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 3)

    def test_instructor_can_retrieve_file_details(self):
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
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], str(file_obj.id))
        self.assertEqual(response.data["category"], File.Category.PATHOLOGY)
        self.assertTrue(response.data["requires_pagination"])

    def test_student_cannot_list_files(self):
        """Test that student cannot list files directly."""
        self.client.force_authenticate(user=self.student_user)
        
        File.objects.create(
            patient=self.patient,
            file=self._create_test_pdf(),
            display_name="test.pdf",
            category=File.Category.IMAGING,
        )

        url = self._get_file_list_url()
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


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
    def setUpTestData(cls):
        """Set up test data for all tests in this class."""
        cls.instructor_group, _ = Group.objects.get_or_create(
            name=Role.INSTRUCTOR.value
        )
        cls.instructor_user = get_user_model().objects.create_user(
            username="test_instructor",
            email="instructor@test.com",
            password="testpass123",
        )
        cls.instructor_user.groups.add(cls.instructor_group)

    def setUp(self):
        """Set up test fixtures for each test method."""
        self.client = APIClient()
        self.client.force_authenticate(user=self.instructor_user)
        self.media_root = settings.MEDIA_ROOT
        
        # Create test patient
        self.patient = Patient.objects.create(
            first_name="Test",
            last_name="Patient",
            date_of_birth="1990-01-01",
            email="test@example.com",
        )

    @classmethod
    def tearDownClass(cls):
        """Clean up after all tests in this class."""
        try:
            if os.path.isdir(settings.MEDIA_ROOT):
                shutil.rmtree(settings.MEDIA_ROOT, ignore_errors=True)
        finally:
            super().tearDownClass()

    def _create_pdf_with_binary_content(self, filename="test.pdf"):
        """
        Create a PDF file with binary content that includes non-UTF-8 bytes.
        
        This simulates real PDF files which contain binary data that cannot
        be decoded as UTF-8. The byte sequence 0xe2 was specifically causing
        errors before the parser fix.
        """
        # Create PDF with binary content including problematic bytes
        pdf_content = b'%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n'
        pdf_content += b'\xe2\x80\x99'  # Non-UTF-8 byte sequence (right single quotation mark)
        pdf_content += b'\n2 0 obj\n<<\n/Type /Pages\n>>\nendobj\n'
        pdf_content += b'%%EOF'
        
        return SimpleUploadedFile(
            name=filename,
            content=pdf_content,
            content_type="application/pdf"
        )

    def test_upload_pdf_with_binary_content(self):
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
        
        pdf_file = self._create_pdf_with_binary_content("Admission Proforma Toni Baxter.pdf")
        data = {
            "file": pdf_file,
            "category": File.Category.ADMISSION,
            "requires_pagination": False,
        }
        
        response = self.client.post(url, data, format="multipart")
        
        # Verify successful upload
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("id", response.data)
        self.assertEqual(response.data["category"], File.Category.ADMISSION)
        self.assertFalse(response.data["requires_pagination"])
        self.assertEqual(response.data["display_name"], "Admission Proforma Toni Baxter.pdf")
        
        # Verify file was created in database
        file_obj = File.objects.get(id=response.data["id"])
        self.assertEqual(file_obj.patient, self.patient)
        self.assertEqual(file_obj.category, File.Category.ADMISSION)
        self.assertFalse(file_obj.requires_pagination)
        
        # Verify file was saved to disk
        self.assertTrue(os.path.exists(file_obj.file.path))

    def test_upload_pdf_with_binary_content_and_pagination(self):
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
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data["requires_pagination"])
        self.assertEqual(response.data["category"], File.Category.IMAGING)
        
        file_obj = File.objects.get(id=response.data["id"])
        self.assertTrue(file_obj.requires_pagination)

    def test_upload_multiple_pdfs_with_binary_content(self):
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
            
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            self.assertEqual(response.data["category"], category)
        
        # Verify all files were created
        self.assertEqual(File.objects.filter(patient=self.patient).count(), 3)

    def test_upload_pdf_via_legacy_endpoint(self):
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
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["category"], File.Category.LAB_RESULTS)
        
        # Verify file was created
        file_obj = File.objects.filter(patient=self.patient).first()
        self.assertIsNotNone(file_obj)
        self.assertEqual(file_obj.display_name, "legacy_upload.pdf")

    def test_multipart_parser_with_mixed_content_types(self):
        """
        Test that multipart parser correctly handles requests with mixed content.
        
        This test verifies that the parser can handle both:
        - Binary file data (PDF with non-UTF-8 bytes)
        - Text form fields (category, requires_pagination)
        """
        url = reverse("file-list", kwargs={"patient_pk": self.patient.id})
        
        # Create PDF with various binary sequences
        pdf_content = b'%PDF-1.4\n'
        pdf_content += b'\x00\x01\x02\x03'  # Binary bytes
        pdf_content += b'\xe2\x80\x93'  # En dash (UTF-8 multi-byte)
        pdf_content += b'\xff\xfe'  # BOM marker
        pdf_content += b'%%EOF'
        
        pdf_file = SimpleUploadedFile(
            name="mixed_content.pdf",
            content=pdf_content,
            content_type="application/pdf"
        )
        
        data = {
            "file": pdf_file,
            "category": File.Category.DIAGNOSTICS,
            "requires_pagination": True,
        }
        
        response = self.client.post(url, data, format="multipart")
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["category"], File.Category.DIAGNOSTICS)
        self.assertTrue(response.data["requires_pagination"])

    def test_parser_preserves_binary_file_integrity(self):
        """
        Test that binary file content is preserved during upload.
        
        This verifies that the multipart parser does not corrupt or alter
        the binary content of uploaded files.
        """
        url = reverse("file-list", kwargs={"patient_pk": self.patient.id})
        
        # Create specific binary content to verify
        original_content = b'%PDF-1.4\n\xe2\x80\x99\xff\xfe\x00\x01%%EOF'
        pdf_file = SimpleUploadedFile(
            name="integrity_test.pdf",
            content=original_content,
            content_type="application/pdf"
        )
        
        data = {
            "file": pdf_file,
            "category": File.Category.OTHER,
        }
        
        response = self.client.post(url, data, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Read the saved file and verify content matches
        file_obj = File.objects.get(id=response.data["id"])
        with open(file_obj.file.path, 'rb') as f:
            saved_content = f.read()
        
        self.assertEqual(saved_content, original_content)
