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
