"""
Test patient filtering in student_groups GET endpoints.

This test verifies that the optional patient query parameter works correctly
in BaseObservationViewSet and BaseStudentRequestViewSet.
"""

from django.contrib.auth.models import Group, User
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from patients.models import Patient
from student_groups.models import (
    BloodPressure,
    BloodTestRequest,
    HeartRate,
    ImagingRequest,
)


class PatientFilteringTestCase(TestCase):
    """Test patient filtering in student_groups endpoints"""

    @classmethod
    def setUpTestData(cls) -> None:
        """Create DB fixtures once per class to speed up tests."""
        # Get or create student group
        student_group, _ = Group.objects.get_or_create(name="student")

        # Create two student users (representing two different groups)
        cls.student1 = User.objects.create_user(
            username="student_group1",
            password="test123",
        )
        cls.student1.groups.add(student_group)

        cls.student2 = User.objects.create_user(
            username="student_group2",
            password="test123",
        )
        cls.student2.groups.add(student_group)

        # Create two patients
        cls.patient1 = Patient.objects.create(
            first_name="John",
            last_name="Doe",
            date_of_birth="1990-01-01",
            mrn="MRN001",
            ward="Ward A",
            bed="Bed 1",
            phone_number="+1111111111",
        )
        cls.patient2 = Patient.objects.create(
            first_name="Jane",
            last_name="Smith",
            date_of_birth="1985-05-15",
            mrn="MRN002",
            ward="Ward B",
            bed="Bed 2",
            phone_number="+2222222222",
        )

        # Create observations for student1
        cls.bp1_patient1 = BloodPressure.objects.create(
            patient=cls.patient1,
            user=cls.student1,
            systolic=120,
            diastolic=80,
        )
        cls.bp2_patient2 = BloodPressure.objects.create(
            patient=cls.patient2,
            user=cls.student1,
            systolic=130,
            diastolic=85,
        )

        cls.hr1_patient1 = HeartRate.objects.create(
            patient=cls.patient1,
            user=cls.student1,
            heart_rate=72,
        )
        cls.hr2_patient2 = HeartRate.objects.create(
            patient=cls.patient2,
            user=cls.student1,
            heart_rate=80,
        )

        # Create observations for student2
        cls.bp3_patient1 = BloodPressure.objects.create(
            patient=cls.patient1,
            user=cls.student2,
            systolic=140,
            diastolic=90,
        )

        # Create requests for student1
        cls.imaging_req1 = ImagingRequest.objects.create(
            patient=cls.patient1,
            user=cls.student1,
            test_type="X-ray",
            name="Dr. Smith",
            role="Physician",
            details="Test",
            infection_control_precautions="None",
            imaging_focus="Chest",
        )
        cls.imaging_req2 = ImagingRequest.objects.create(
            patient=cls.patient2,
            user=cls.student1,
            test_type="MRI scan",
            name="Dr. Jones",
            role="Physician",
            details="Test",
            infection_control_precautions="None",
            imaging_focus="Head",
        )

        cls.blood_test_req1 = BloodTestRequest.objects.create(
            patient=cls.patient1,
            user=cls.student1,
            name="Dr. Smith",
            role="Physician",
            test_types=[BloodTestRequest.TestType.FBC],
            details="Routine check",
        )

    def setUp(self) -> None:
        # Setup a fresh API client per test
        self.client = APIClient()

    def test_blood_pressure_without_patient_filter(self) -> None:
        """Test blood pressure list without patient filter returns all user's records"""
        self.client.force_authenticate(user=self.student1)
        response = self.client.get("/api/student-groups/observations/blood-pressures/")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 2  # Both patients for student1

    def test_blood_pressure_with_patient_filter(self) -> None:
        """Test blood pressure list with patient filter returns only specified patient's records"""
        self.client.force_authenticate(user=self.student1)
        response = self.client.get(
            f"/api/student-groups/observations/blood-pressures/?patient={self.patient1.id}",
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 1
        assert response.data["results"][0]["patient"] == self.patient1.id

    def test_heart_rate_with_patient_filter(self) -> None:
        """Test heart rate list with patient filter"""
        self.client.force_authenticate(user=self.student1)
        response = self.client.get(
            f"/api/student-groups/observations/heart-rates/?patient={self.patient2.id}",
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 1
        assert response.data["results"][0]["patient"] == self.patient2.id

    def test_patient_filter_respects_user_isolation(self) -> None:
        """Test that patient filter doesn't allow accessing other users' data"""
        self.client.force_authenticate(user=self.student2)
        response = self.client.get(
            f"/api/student-groups/observations/blood-pressures/?patient={self.patient1.id}",
        )

        assert response.status_code == status.HTTP_200_OK
        # student2 has only 1 record for patient1
        assert response.data["count"] == 1
        # Verify it's student2's record, not student1's
        assert response.data["results"][0]["user"] == self.student2.id

    def test_imaging_request_without_patient_filter(self) -> None:
        """Test imaging request list without patient filter"""
        self.client.force_authenticate(user=self.student1)
        response = self.client.get("/api/student-groups/imaging-requests/")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 2  # Both patients for student1

    def test_imaging_request_with_patient_filter(self) -> None:
        """Test imaging request list with patient filter"""
        self.client.force_authenticate(user=self.student1)
        response = self.client.get(
            f"/api/student-groups/imaging-requests/?patient={self.patient1.id}",
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 1
        assert response.data["results"][0]["patient"] == self.patient1.id

    def test_blood_test_request_with_patient_filter(self) -> None:
        """Test blood test request with patient filter"""
        self.client.force_authenticate(user=self.student1)
        response = self.client.get(
            f"/api/student-groups/blood-test-requests/?patient={self.patient1.id}",
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 1
        assert response.data["results"][0]["patient"] == self.patient1.id

    def test_invalid_patient_id_returns_empty_list(self) -> None:
        """Test that invalid patient ID returns empty list, not error"""
        self.client.force_authenticate(user=self.student1)
        response = self.client.get(
            "/api/student-groups/observations/blood-pressures/?patient=999999",
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 0

    def test_patient_filter_with_multiple_observation_types(self) -> None:
        """Test that patient filter works consistently across different observation types"""
        self.client.force_authenticate(user=self.student1)

        # Blood pressure for patient1
        bp_response = self.client.get(
            f"/api/student-groups/observations/blood-pressures/?patient={self.patient1.id}",
        )
        assert bp_response.status_code == status.HTTP_200_OK
        assert bp_response.data["count"] == 1

        # Heart rate for patient1
        hr_response = self.client.get(
            f"/api/student-groups/observations/heart-rates/?patient={self.patient1.id}",
        )
        assert hr_response.status_code == status.HTTP_200_OK
        assert hr_response.data["count"] == 1

        # Both should be for the same patient
        assert (
            bp_response.data["results"][0]["patient"]
            == hr_response.data["results"][0]["patient"]
        )

    def test_backward_compatibility_notes_endpoint(self) -> None:
        """Test that notes endpoint also supports patient filtering"""
        from student_groups.models import Note

        # Create notes for both patients
        Note.objects.create(
            patient=self.patient1,
            user=self.student1,
            name="Dr. Smith",
            role="Physician",
            content="Test note for patient 1",
        )
        Note.objects.create(
            patient=self.patient2,
            user=self.student1,
            name="Dr. Jones",
            role="Nurse",
            content="Test note for patient 2",
        )

        self.client.force_authenticate(user=self.student1)

        # Without filter
        response_all = self.client.get("/api/student-groups/notes/")
        assert response_all.status_code == status.HTTP_200_OK
        assert response_all.data["count"] == 2

        # With filter
        response_filtered = self.client.get(
            f"/api/student-groups/notes/?patient={self.patient1.id}",
        )
        assert response_filtered.status_code == status.HTTP_200_OK
        assert response_filtered.data["count"] == 1
        assert response_filtered.data["results"][0]["patient"] == self.patient1.id
