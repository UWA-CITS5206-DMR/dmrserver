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
from student_groups.models import ImagingRequest, ApprovedFile
from core.context import Role


class FileAccessIntegrationTest(TestCase):
    def setUp(self):
        """Set up test data"""
        # Get or create groups
        self.admin_group, _ = Group.objects.get_or_create(name=Role.ADMIN.value)
        self.instructor_group, _ = Group.objects.get_or_create(
            name=Role.INSTRUCTOR.value
        )
        self.student_group, _ = Group.objects.get_or_create(name=Role.STUDENT.value)

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

        # Create imaging request
        self.imaging_request = ImagingRequest.objects.create(
            user=self.student,
            patient=self.patient,
            test_type=ImagingRequest.TestType.X_RAY,
            reason="Test imaging request for file integration test",
            name="Dr. Test",
            role="Doctor",
            status="completed",
        )

        # Create approved file
        self.approved_file = ApprovedFile.objects.create(
            imaging_request=self.imaging_request, file=self.file, page_range="1-3"
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

        response = self.client.get(url, {"page_range": "4"})

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

        response = self.client.get(url, {"page_range": "2"})

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

    def test_instructor_custom_page_range_access(self):
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
            "file-view", kwargs={"patient_pk": self.patient.id, "pk": self.file.id}
        )

        # Test 1: Instructor can access a single page using page_range
        response = self.client.get(url, {"page_range": "5"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response["Content-Type"], "application/pdf")

        # Test 2: Instructor can access a custom range using page_range parameter
        response = self.client.get(url, {"page_range": "1-5"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response["Content-Type"], "application/pdf")

        # Test 3: Instructor can access pages outside student's approved range
        # Student approved range is "1-3", instructor should access page 4
        response = self.client.get(url, {"page_range": "4"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response["Content-Type"], "application/pdf")

        # Test 4: Instructor can access complex ranges
        response = self.client.get(url, {"page_range": "1-2,4-5"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response["Content-Type"], "application/pdf")

    def test_admin_custom_page_range_access(self):
        """
        Test that admins can specify custom page ranges for paginated files.

        Similar to instructors, admins should have unrestricted access.
        """
        # Enable pagination for the file
        self.file.requires_pagination = True
        self.file.save()

        self.client.force_authenticate(user=self.admin)
        url = reverse(
            "file-view", kwargs={"patient_pk": self.patient.id, "pk": self.file.id}
        )

        # Admin can access any single page using page_range
        response = self.client.get(url, {"page_range": "5"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response["Content-Type"], "application/pdf")

        # Admin can access any range using page_range parameter
        response = self.client.get(url, {"page_range": "1-5"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response["Content-Type"], "application/pdf")

    def test_student_cannot_access_pages_outside_approved_range(self):
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
            "file-view", kwargs={"patient_pk": self.patient.id, "pk": self.file.id}
        )

        # Student approved range is "1-3"
        # Test 1: Access within approved range should succeed
        response = self.client.get(url, {"page_range": "2"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Test 2: Access outside approved range should fail
        response = self.client.get(url, {"page_range": "4"})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn("not authorized", response.content.decode().lower())

        # Test 3: Range partially outside approved range should fail
        response = self.client.get(url, {"page_range": "2-5"})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn("not authorized", response.content.decode().lower())

    def test_student_can_access_approved_file_from_blood_test_request(self):
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
                "blood_test.pdf", pdf_content, content_type="application/pdf"
            ),
            display_name="Blood Test Results",
            requires_pagination=False,
        )

        # Create blood test request
        blood_test_request = BloodTestRequest.objects.create(
            user=self.student,
            patient=self.patient,
            test_type=BloodTestRequest.TestType.FBC,
            reason="Test blood test request for file integration test",
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
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response["Content-Type"], "application/pdf")

    def test_student_can_access_paginated_file_from_blood_test_request(self):
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
                "blood_test_paginated.pdf", pdf_content, content_type="application/pdf"
            ),
            display_name="Blood Test Results (Paginated)",
            requires_pagination=True,
        )

        # Create blood test request
        blood_test_request = BloodTestRequest.objects.create(
            user=self.student,
            patient=self.patient,
            test_type=BloodTestRequest.TestType.EUC,
            reason="Test paginated blood test file access",
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
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response["Content-Type"], "application/pdf")

        # Test 2: Access range within approved range (should succeed)
        response = self.client.get(url, {"page_range": "2-3"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response["Content-Type"], "application/pdf")

        # Test 3: Access page outside approved range (should fail)
        response = self.client.get(url, {"page_range": "5"})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn("not authorized", response.content.decode().lower())
