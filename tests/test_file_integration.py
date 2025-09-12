"""
Integration tests for file access permissions in real scenarios.
Tests the complete flow from lab request approval to file access.
"""

from django.test import TestCase
from django.contrib.auth.models import User, Group
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from django.core.files.uploadedfile import SimpleUploadedFile

from patients.models import Patient, File
from student_groups.models import LabRequest, ApprovedFile


class FileAccessIntegrationTest(TestCase):
    def setUp(self):
        """Set up test data"""
        # Get or create groups
        self.admin_group, _ = Group.objects.get_or_create(name="admin")
        self.instructor_group, _ = Group.objects.get_or_create(name="instructor")
        self.student_group, _ = Group.objects.get_or_create(name="student")

        # Create users
        self.student = User.objects.create_user("student1", "student@test.com", "pass")
        self.instructor = User.objects.create_user(
            "instructor1", "instructor@test.com", "pass"
        )
        self.admin = User.objects.create_user("admin1", "admin@test.com", "pass")

        # Assign roles
        self.student.groups.add(self.student_group)
        self.instructor.groups.add(self.instructor_group)
        self.admin.groups.add(self.admin_group)

        # Create patient
        self.patient = Patient.objects.create(
            first_name="John",
            last_name="Doe",
            date_of_birth="1990-01-01",
            email="john.doe@example.com",
        )

        # Create a PDF file
        pdf_content = self._create_test_pdf()
        self.file = File.objects.create(
            patient=self.patient,
            file=SimpleUploadedFile(
                "test.pdf", pdf_content, content_type="application/pdf"
            ),
            display_name="Test PDF",
            requires_pagination=False,  # Use simple non-paginated file for testing
        )

        # Create lab request
        self.lab_request = LabRequest.objects.create(
            user=self.student, patient=self.patient, status="completed"
        )

        # Create approved file
        self.approved_file = ApprovedFile.objects.create(
            lab_request=self.lab_request, file=self.file, page_range="1-3"
        )

        self.client = APIClient()

    def _create_test_pdf(self):
        """Create a simple test PDF with multiple pages"""
        # Create a minimal PDF content for testing
        # This is a simple PDF with basic structure
        pdf_content = b"""%PDF-1.4
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
>>
endobj

2 0 obj
<<
/Type /Pages
/Kids [3 0 R 4 0 R 5 0 R 6 0 R 7 0 R]
/Count 5
>>
endobj

3 0 obj
<<
/Type /Page
/Parent 2 0 R
/Contents 8 0 R
>>
endobj

4 0 obj
<<
/Type /Page
/Parent 2 0 R
/Contents 9 0 R
>>
endobj

5 0 obj
<<
/Type /Page
/Parent 2 0 R
/Contents 10 0 R
>>
endobj

6 0 obj
<<
/Type /Page
/Parent 2 0 R
/Contents 11 0 R
>>
endobj

7 0 obj
<<
/Type /Page
/Parent 2 0 R
/Contents 12 0 R
>>
endobj

8 0 obj
<<
/Length 44
>>
stream
BT
/F1 12 Tf
72 720 Td
(Page 1) Tj
ET
endstream
endobj

9 0 obj
<<
/Length 44
>>
stream
BT
/F1 12 Tf
72 720 Td
(Page 2) Tj
ET
endstream
endobj

10 0 obj
<<
/Length 44
>>
stream
BT
/F1 12 Tf
72 720 Td
(Page 3) Tj
ET
endstream
endobj

11 0 obj
<<
/Length 44
>>
stream
BT
/F1 12 Tf
72 720 Td
(Page 4) Tj
ET
endstream
endobj

12 0 obj
<<
/Length 44
>>
stream
BT
/F1 12 Tf
72 720 Td
(Page 5) Tj
ET
endstream
endobj

xref
0 13
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000123 00000 n 
0000000190 00000 n 
0000000257 00000 n 
0000000324 00000 n 
0000000391 00000 n 
0000000458 00000 n 
0000000552 00000 n 
0000000646 00000 n 
0000000741 00000 n 
0000000836 00000 n 
trailer
<<
/Size 13
/Root 1 0 R
>>
startxref
931
%%EOF"""
        return pdf_content

    def test_student_can_access_approved_file(self):
        """Test that student can access file they have approval for"""
        self.client.force_authenticate(user=self.student)

        url = reverse(
            "file-view", kwargs={"patient_pk": self.patient.id, "pk": self.file.id}
        )

        response = self.client.get(url)

        # Should be successful
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response["Content-Type"], "application/pdf")

    def test_student_cannot_access_unapproved_file(self):
        """Test that student cannot access file without approval"""
        # Delete the approved file
        self.approved_file.delete()

        self.client.force_authenticate(user=self.student)

        url = reverse(
            "file-view", kwargs={"patient_pk": self.patient.id, "pk": self.file.id}
        )

        response = self.client.get(url)

        # Should be forbidden
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_instructor_can_access_any_file(self):
        """Test that instructor can access any file"""
        self.client.force_authenticate(user=self.instructor)

        url = reverse(
            "file-view", kwargs={"patient_pk": self.patient.id, "pk": self.file.id}
        )

        response = self.client.get(url)

        # Should be successful
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response["Content-Type"], "application/pdf")

    def test_student_page_range_enforcement(self):
        """Test that student can only access approved page range"""
        # Change file to require pagination
        self.file.requires_pagination = True
        self.file.save()

        self.client.force_authenticate(user=self.student)

        # Try to access page 4 (not in approved range 1-3)
        url = reverse(
            "file-view", kwargs={"patient_pk": self.patient.id, "pk": self.file.id}
        )

        response = self.client.get(url, {"page": "4"})

        # Should be forbidden
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_student_can_access_approved_pages(self):
        """Test that student can access pages within approved range"""
        # Change file to require pagination
        self.file.requires_pagination = True
        self.file.save()

        self.client.force_authenticate(user=self.student)

        # Try to access page 2 (within approved range 1-3)
        url = reverse(
            "file-view", kwargs={"patient_pk": self.patient.id, "pk": self.file.id}
        )

        response = self.client.get(url, {"page": "2"})

        # Should be successful
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response["Content-Type"], "application/pdf")

    def test_student_cannot_manage_files(self):
        """Test that student cannot perform CRUD operations on files"""
        self.client.force_authenticate(user=self.student)

        # Try to create a file
        url = reverse("file-list", kwargs={"patient_pk": self.patient.id})
        response = self.client.post(url, {})

        # Should be forbidden
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_instructor_can_manage_files(self):
        """Test that instructor can perform CRUD operations on files"""
        self.client.force_authenticate(user=self.instructor)

        # Try to list files
        url = reverse("file-list", kwargs={"patient_pk": self.patient.id})
        response = self.client.get(url)

        # Should be successful
        self.assertEqual(response.status_code, status.HTTP_200_OK)
