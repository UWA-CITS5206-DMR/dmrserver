from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from core.context import Role
from patients.models import Patient
from student_groups.models import (
    BloodPressure,
    BloodSugar,
    BodyTemperature,
    HeartRate,
    Note,
    ObservationManager,
    OxygenSaturation,
    PainScore,
    RespiratoryRate,
)
from student_groups.serializers import NoteSerializer, ObservationsSerializer


class NoteModelTest(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.user = get_user_model().objects.create_user(
            username="testuser",
            password="password",
        )
        cls.patient = Patient.objects.create(
            first_name="John",
            last_name="Doe",
            date_of_birth="1990-01-01",
            mrn="MRN_SG_001",
            ward="Ward SG",
            bed="Bed 1",
            email="john.doe@example.com",
        )

    def test_create_note(self) -> None:
        note = Note.objects.create(
            patient=self.patient,
            user=self.user,
            name="Dr. Smith",
            role="Doctor",
            content="This is a test note.",
        )
        assert note.patient == self.patient
        assert note.user == self.user
        assert note.name == "Dr. Smith"
        assert note.role == "Doctor"
        assert note.content == "This is a test note."
        assert note.created_at is not None
        assert note.updated_at is not None
        assert (
            str(note) == f"Note for {self.patient} by Dr. Smith ({self.user.username})"
        )


class BloodPressureModelTest(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.user = get_user_model().objects.create_user(
            username="testuser",
            password="password",
        )
        cls.patient = Patient.objects.create(
            first_name="John",
            last_name="Doe",
            date_of_birth="1990-01-01",
            mrn="MRN_SG_002",
            ward="Ward SG",
            bed="Bed 2",
            email="john.doe@example.com",
        )

    def test_create_blood_pressure(self) -> None:
        blood_pressure = BloodPressure.objects.create(
            patient=self.patient,
            user=self.user,
            systolic=120,
            diastolic=80,
        )
        assert blood_pressure.patient == self.patient
        assert blood_pressure.user == self.user
        assert blood_pressure.systolic == 120
        assert blood_pressure.diastolic == 80
        assert blood_pressure.created_at is not None
        assert (
            str(blood_pressure)
            == f"{self.patient} - 120/80 mmHg ({self.user.username})"
        )


class HeartRateModelTest(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.user = get_user_model().objects.create_user(
            username="testuser",
            password="password",
        )
        cls.patient = Patient.objects.create(
            first_name="John",
            last_name="Doe",
            date_of_birth="1990-01-01",
            mrn="MRN_SG_003",
            ward="Ward SG",
            bed="Bed 3",
            email="john.doe@example.com",
        )

    def test_create_heart_rate(self) -> None:
        heart_rate = HeartRate.objects.create(
            patient=self.patient,
            user=self.user,
            heart_rate=72,
        )
        assert heart_rate.patient == self.patient
        assert heart_rate.user == self.user
        assert heart_rate.heart_rate == 72
        assert heart_rate.created_at is not None
        assert str(heart_rate) == f"{self.patient} - 72 bpm ({self.user.username})"


class BodyTemperatureModelTest(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.user = get_user_model().objects.create_user(
            username="testuser",
            password="password",
        )
        cls.patient = Patient.objects.create(
            first_name="John",
            last_name="Doe",
            date_of_birth="1990-01-01",
            mrn="MRN_SG_004",
            ward="Ward SG",
            bed="Bed 4",
            email="john.doe@example.com",
        )

    def test_create_body_temperature(self) -> None:
        body_temperature = BodyTemperature.objects.create(
            patient=self.patient,
            user=self.user,
            temperature=Decimal("36.6"),
        )
        assert body_temperature.patient == self.patient
        assert body_temperature.user == self.user
        assert body_temperature.temperature == Decimal("36.6")
        assert body_temperature.created_at is not None
        assert (
            str(body_temperature) == f"{self.patient} - 36.6°C ({self.user.username})"
        )

    def test_body_temperature_validation(self) -> None:
        with pytest.raises(ValidationError):
            BodyTemperature.objects.create(
                patient=self.patient,
                user=self.user,
                temperature="50.0",
            )


class ObservationManagerTest(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.user = get_user_model().objects.create_user(
            username="testuser",
            password="password",
        )
        cls.patient = Patient.objects.create(
            first_name="John",
            last_name="Doe",
            date_of_birth="1990-01-01",
            mrn="MRN_SG_005",
            ward="Ward SG",
            bed="Bed 5",
            email="john.doe@example.com",
        )
        BloodPressure.objects.create(
            patient=cls.patient,
            user=cls.user,
            systolic=120,
            diastolic=80,
        )
        HeartRate.objects.create(patient=cls.patient, user=cls.user, heart_rate=72)
        BodyTemperature.objects.create(
            patient=cls.patient,
            user=cls.user,
            temperature="36.6",
        )
        RespiratoryRate.objects.create(
            patient=cls.patient,
            user=cls.user,
            respiratory_rate=16,
        )
        BloodSugar.objects.create(
            patient=cls.patient,
            user=cls.user,
            sugar_level="100.0",
        )
        OxygenSaturation.objects.create(
            patient=cls.patient,
            user=cls.user,
            saturation_percentage=98,
        )

    def test_get_observations_by_user_and_patient(self) -> None:
        observations = ObservationManager.get_observations_by_user_and_patient(
            self.user.id,
            self.patient.id,
        )
        assert "blood_pressures" in observations
        assert "heart_rates" in observations
        assert "body_temperatures" in observations
        assert "respiratory_rates" in observations
        assert "blood_sugars" in observations
        assert "oxygen_saturations" in observations

        assert observations["blood_pressures"].count() == 1
        assert observations["heart_rates"].count() == 1
        assert observations["body_temperatures"].count() == 1
        assert observations["respiratory_rates"].count() == 1
        assert observations["blood_sugars"].count() == 1
        assert observations["oxygen_saturations"].count() == 1
        assert observations["blood_pressures"].first().systolic == 120
        assert observations["heart_rates"].first().heart_rate == 72
        assert observations["body_temperatures"].first().temperature == Decimal("36.6")
        assert observations["respiratory_rates"].first().respiratory_rate == 16
        assert observations["blood_sugars"].first().sugar_level == Decimal("100.0")
        assert observations["oxygen_saturations"].first().saturation_percentage == 98

    def test_create_observations(self) -> None:
        observation_data = {
            "blood_pressure": {
                "patient": self.patient,
                "user": self.user,
                "systolic": 130,
                "diastolic": 85,
            },
            "heart_rate": {
                "patient": self.patient,
                "user": self.user,
                "heart_rate": 80,
            },
            "respiratory_rate": {
                "patient": self.patient,
                "user": self.user,
                "respiratory_rate": 18,
            },
            "blood_sugar": {
                "patient": self.patient,
                "user": self.user,
                "sugar_level": "110.0",
            },
            "oxygen_saturation": {
                "patient": self.patient,
                "user": self.user,
                "saturation_percentage": 97,
            },
        }
        BloodPressure.objects.all().delete()
        HeartRate.objects.all().delete()
        BodyTemperature.objects.all().delete()
        RespiratoryRate.objects.all().delete()
        BloodSugar.objects.all().delete()
        OxygenSaturation.objects.all().delete()

        created_instances = ObservationManager.create_observations(observation_data)

        assert BloodPressure.objects.count() == 1
        assert HeartRate.objects.count() == 1
        assert BodyTemperature.objects.count() == 0
        assert RespiratoryRate.objects.count() == 1
        assert BloodSugar.objects.count() == 1
        assert OxygenSaturation.objects.count() == 1

        assert "blood_pressure" in created_instances
        assert "heart_rate" in created_instances
        assert "body_temperature" not in created_instances
        assert "respiratory_rate" in created_instances
        assert "blood_sugar" in created_instances
        assert "oxygen_saturation" in created_instances

        bp = BloodPressure.objects.first()
        assert bp.systolic == 130
        assert bp.diastolic == 85

        hr = HeartRate.objects.first()
        assert hr.heart_rate == 80

        rr = RespiratoryRate.objects.first()
        assert rr.respiratory_rate == 18

        bs = BloodSugar.objects.first()
        assert bs.sugar_level == Decimal("110.0")

        os = OxygenSaturation.objects.first()
        assert os.saturation_percentage == 97


class NoteSerializerTest(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.user = get_user_model().objects.create_user(
            username="testuser",
            password="password",
        )
        cls.patient = Patient.objects.create(
            first_name="John",
            last_name="Doe",
            date_of_birth="1990-01-01",
            mrn="MRN_SG_006",
            ward="Ward SG",
            bed="Bed 6",
            email="john.doe@example.com",
        )
        cls.note_data = {
            "patient": cls.patient.id,
            "user": cls.user.id,
            "name": "Dr. Smith",
            "role": "Doctor",
            "content": "This is a test note.",
        }

    def test_note_serializer_valid(self) -> None:
        serializer = NoteSerializer(data=self.note_data)
        assert serializer.is_valid(raise_exception=True)

    def test_note_serializer_invalid_no_content(self) -> None:
        invalid_data = self.note_data.copy()
        invalid_data["content"] = ""
        serializer = NoteSerializer(data=invalid_data)
        assert not serializer.is_valid()
        assert "content" in serializer.errors

    def test_note_serializer_invalid_no_name(self) -> None:
        invalid_data = self.note_data.copy()
        invalid_data["name"] = ""
        serializer = NoteSerializer(data=invalid_data)
        assert not serializer.is_valid()
        assert "name" in serializer.errors


class ObservationsSerializerTest(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.user = get_user_model().objects.create_user(
            username="testuser",
            password="password",
        )
        cls.patient = Patient.objects.create(
            first_name="John",
            last_name="Doe",
            date_of_birth="1990-01-01",
            mrn="MRN_SG_007",
            ward="Ward SG",
            bed="Bed 7",
            email="john.doe@example.com",
        )
        cls.observation_data = {
            "blood_pressure": {
                "patient": cls.patient.id,
                "user": cls.user.id,
                "systolic": 120,
                "diastolic": 80,
            },
            "heart_rate": {
                "patient": cls.patient.id,
                "user": cls.user.id,
                "heart_rate": 72,
            },
            "body_temperature": {
                "patient": cls.patient.id,
                "user": cls.user.id,
                "temperature": "36.6",
            },
            "respiratory_rate": {
                "patient": cls.patient.id,
                "user": cls.user.id,
                "respiratory_rate": 16,
            },
            "blood_sugar": {
                "patient": cls.patient.id,
                "user": cls.user.id,
                "sugar_level": "100.0",
            },
            "oxygen_saturation": {
                "patient": cls.patient.id,
                "user": cls.user.id,
                "saturation_percentage": 98,
            },
        }

    def test_observations_serializer_valid(self) -> None:
        serializer = ObservationsSerializer(data=self.observation_data)
        assert serializer.is_valid(raise_exception=True)

    def test_observations_serializer_create(self) -> None:
        serializer = ObservationsSerializer(data=self.observation_data)
        assert serializer.is_valid(raise_exception=True)
        created_objects = serializer.save()
        assert len(created_objects) == 6
        assert "blood_pressure" in created_objects
        assert "heart_rate" in created_objects
        assert "body_temperature" in created_objects
        assert "respiratory_rate" in created_objects
        assert "blood_sugar" in created_objects
        assert "oxygen_saturation" in created_objects

    def test_observations_serializer_invalid_data(self) -> None:
        invalid_data = self.observation_data.copy()
        invalid_data["blood_pressure"]["systolic"] = "invalid"
        serializer = ObservationsSerializer(data=invalid_data)
        assert not serializer.is_valid()
        assert "blood_pressure" in serializer.errors


class NoteViewSetTest(APITestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.student_group, created = Group.objects.get_or_create(
            name=Role.STUDENT.value,
        )
        cls.user = get_user_model().objects.create_user(
            username="testuser",
            password="password",
        )
        cls.user.groups.add(cls.student_group)
        cls.patient = Patient.objects.create(
            first_name="John",
            last_name="Doe",
            date_of_birth="1990-01-01",
            mrn="MRN400",
            ward="Ward G",
            bed="Bed 7",
            email="john.doe@example.com",
        )
        cls.note = Note.objects.create(
            patient=cls.patient,
            user=cls.user,
            name="Dr. Smith",
            role="Doctor",
            content="Test note",
        )

    def setUp(self) -> None:
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_list_notes(self) -> None:
        response = self.client.get(reverse("note-list"))
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 1

    def test_create_note(self) -> None:
        data = {
            "patient": self.patient.id,
            "name": "Dr. Jones",
            "role": "Doctor",
            "content": "New test note",
        }
        response = self.client.post(reverse("note-list"), data, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        assert Note.objects.count() == 2
        assert response.data["name"] == "Dr. Jones"

    def test_retrieve_note(self) -> None:
        response = self.client.get(reverse("note-detail", args=[self.note.id]))
        assert response.status_code == status.HTTP_200_OK
        assert response.data["name"] == "Dr. Smith"
        assert response.data["content"] == "Test note"

    def test_update_note(self) -> None:
        data = {"name": "Dr. Brown", "content": "Updated test note"}
        response = self.client.patch(
            reverse("note-detail", args=[self.note.id]),
            data,
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        self.note.refresh_from_db()
        assert self.note.name == "Dr. Brown"
        assert self.note.content == "Updated test note"

    def test_delete_note(self) -> None:
        response = self.client.delete(reverse("note-detail", args=[self.note.id]))
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert Note.objects.count() == 0


class ObservationsViewSetTest(APITestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.student_group, created = Group.objects.get_or_create(
            name=Role.STUDENT.value,
        )
        cls.user = get_user_model().objects.create_user(
            username="testuser",
            password="password",
        )
        cls.user.groups.add(cls.student_group)
        cls.patient = Patient.objects.create(
            first_name="John",
            last_name="Doe",
            date_of_birth="1990-01-01",
            mrn="MRN401",
            ward="Ward H",
            bed="Bed 8",
            email="john.doe@example.com",
        )

    def setUp(self) -> None:
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.observation_data = {
            "blood_pressure": {
                "patient": self.patient.id,
                "user": self.user.id,
                "systolic": 120,
                "diastolic": 80,
            },
            "heart_rate": {
                "patient": self.patient.id,
                "user": self.user.id,
                "heart_rate": 72,
            },
            "respiratory_rate": {
                "patient": self.patient.id,
                "user": self.user.id,
                "respiratory_rate": 16,
            },
            "pain_score": {
                "patient": self.patient.id,
                "user": self.user.id,
                "score": 4,
            },
        }

    def test_create_observations(self) -> None:
        response = self.client.post(
            reverse("observation-list"),
            self.observation_data,
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert BloodPressure.objects.count() == 1
        assert HeartRate.objects.count() == 1
        assert RespiratoryRate.objects.count() == 1
        assert PainScore.objects.count() == 1
        assert "blood_pressure" in response.data
        assert "heart_rate" in response.data
        assert "respiratory_rate" in response.data
        assert "pain_score" in response.data

    def test_list_observations(self) -> None:
        BloodPressure.objects.create(
            patient=self.patient,
            user=self.user,
            systolic=120,
            diastolic=80,
        )
        RespiratoryRate.objects.create(
            patient=self.patient,
            user=self.user,
            respiratory_rate=16,
        )
        response = self.client.get(
            reverse("observation-list"),
            {"patient_id": self.patient.id},
        )
        assert response.status_code == status.HTTP_200_OK
        # Check pagination format
        assert "count" in response.data
        assert "next" in response.data
        assert "previous" in response.data
        assert "results" in response.data
        # Check observation data is in results
        assert len(response.data["results"]["blood_pressures"]) == 1
        assert len(response.data["results"]["heart_rates"]) == 0
        assert len(response.data["results"]["respiratory_rates"]) == 1

    def test_list_observations_with_pagination(self) -> None:
        """Test that page_size parameter limits results for each observation type"""
        # Create multiple observations
        for i in range(5):
            BloodPressure.objects.create(
                patient=self.patient,
                user=self.user,
                systolic=120 + i,
                diastolic=80 + i,
            )
            HeartRate.objects.create(
                patient=self.patient,
                user=self.user,
                heart_rate=70 + i,
            )

        # Test with page_size=2
        response = self.client.get(
            reverse("observation-list"),
            {"patient_id": self.patient.id, "page_size": 2},
        )
        assert response.status_code == status.HTTP_200_OK
        # Check pagination format
        assert "count" in response.data
        assert "results" in response.data
        assert len(response.data["results"]["blood_pressures"]) == 2
        assert len(response.data["results"]["heart_rates"]) == 2

        # Test with page_size=1
        response = self.client.get(
            reverse("observation-list"),
            {"patient_id": self.patient.id, "page_size": 1},
        )
        assert response.status_code == status.HTTP_200_OK
        assert "count" in response.data
        assert "results" in response.data
        assert len(response.data["results"]["blood_pressures"]) == 1
        assert len(response.data["results"]["heart_rates"]) == 1

    def test_list_observations_with_ordering(self) -> None:
        """Test that ordering parameter sorts results correctly"""
        from datetime import timedelta

        from django.utils import timezone

        # Create observations with distinct timestamps without sleeping
        now = timezone.now()
        bp_old = BloodPressure.objects.create(
            patient=self.patient,
            user=self.user,
            systolic=120,
            diastolic=80,
        )
        bp_new = BloodPressure.objects.create(
            patient=self.patient,
            user=self.user,
            systolic=130,
            diastolic=85,
        )
        # Set explicit created_at values so ordering tests are deterministic and fast
        BloodPressure.objects.filter(pk=bp_old.pk).update(
            created_at=now - timedelta(milliseconds=10),
        )
        BloodPressure.objects.filter(pk=bp_new.pk).update(created_at=now)

        # Test descending order (newest first) - default
        response = self.client.get(
            reverse("observation-list"),
            {"patient_id": self.patient.id, "ordering": "-created_at"},
        )
        assert response.status_code == status.HTTP_200_OK
        assert "results" in response.data
        assert (
            response.data["results"]["blood_pressures"][0]["systolic"] == 130
        )  # Newest first

        # Test ascending order (oldest first)
        response = self.client.get(
            reverse("observation-list"),
            {"patient_id": self.patient.id, "ordering": "created_at"},
        )
        assert response.status_code == status.HTTP_200_OK
        assert "results" in response.data
        assert (
            response.data["results"]["blood_pressures"][0]["systolic"] == 120
        )  # Oldest first


class RespiratoryRateModelTest(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.user = get_user_model().objects.create_user(
            username="testuser",
            password="password",
        )
        cls.patient = Patient.objects.create(
            first_name="John",
            last_name="Doe",
            date_of_birth="1990-01-01",
            mrn="MRN_SG_008",
            ward="Ward SG",
            bed="Bed 8",
            email="john.doe@example.com",
        )

    def test_create_respiratory_rate(self) -> None:
        respiratory_rate = RespiratoryRate.objects.create(
            patient=self.patient,
            user=self.user,
            respiratory_rate=16,
        )
        assert respiratory_rate.patient == self.patient
        assert respiratory_rate.user == self.user
        assert respiratory_rate.respiratory_rate == 16
        assert respiratory_rate.created_at is not None
        assert (
            str(respiratory_rate)
            == f"{self.patient} - 16 breaths/min ({self.user.username})"
        )


class BloodSugarModelTest(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.user = get_user_model().objects.create_user(
            username="testuser",
            password="password",
        )
        cls.patient = Patient.objects.create(
            first_name="John",
            last_name="Doe",
            date_of_birth="1990-01-01",
            mrn="MRN_SG_009",
            ward="Ward SG",
            bed="Bed 9",
            email="john.doe@example.com",
        )

    def test_create_blood_sugar(self) -> None:
        blood_sugar = BloodSugar.objects.create(
            patient=self.patient,
            user=self.user,
            sugar_level=Decimal("99.5"),
        )
        assert blood_sugar.patient == self.patient
        assert blood_sugar.user == self.user
        assert blood_sugar.sugar_level == Decimal("99.5")
        assert blood_sugar.created_at is not None
        assert str(blood_sugar) == f"{self.patient} - 99.5 mg/dL ({self.user.username})"


class OxygenSaturationModelTest(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.user = get_user_model().objects.create_user(
            username="testuser",
            password="password",
        )
        cls.patient = Patient.objects.create(
            first_name="John",
            last_name="Doe",
            date_of_birth="1990-01-01",
            mrn="MRN_SG_010",
            ward="Ward SG",
            bed="Bed 10",
            email="john.doe@example.com",
        )

    def test_create_oxygen_saturation(self) -> None:
        oxygen_saturation = OxygenSaturation.objects.create(
            patient=self.patient,
            user=self.user,
            saturation_percentage=98,
        )
        assert oxygen_saturation.patient == self.patient
        assert oxygen_saturation.user == self.user
        assert oxygen_saturation.saturation_percentage == 98
        assert oxygen_saturation.created_at is not None
        assert str(oxygen_saturation) == f"{self.patient} - 98% ({self.user.username})"


class PainScoreModelTest(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.user = get_user_model().objects.create_user(
            username="testuser",
            password="password",
        )
        cls.patient = Patient.objects.create(
            first_name="John",
            last_name="Doe",
            date_of_birth="1990-01-01",
            mrn="MRN_SG_011",
            ward="Ward SG",
            bed="Bed 11",
            email="john.doe@example.com",
        )

    def test_create_pain_score(self) -> None:
        pain_score = PainScore.objects.create(
            patient=self.patient,
            user=self.user,
            score=7,
        )
        assert pain_score.patient == self.patient
        assert pain_score.user == self.user
        assert pain_score.score == 7
        assert pain_score.created_at is not None
        assert str(pain_score) == f"{self.patient} - Pain 7/10 ({self.user.username})"

    def test_pain_score_validation_valid_range(self) -> None:
        # Test valid range 0-10
        for score in [0, 5, 10]:
            pain_score = PainScore(patient=self.patient, user=self.user, score=score)
            try:
                pain_score.clean()
                pain_score.save()
                assert pain_score.score == score
            except ValidationError:
                self.fail(f"ValidationError raised for valid score {score}")

    def test_pain_score_validation_invalid_range(self) -> None:
        # Test invalid scores
        for score in [-1, 11, 15]:
            pain_score = PainScore(patient=self.patient, user=self.user, score=score)
            with pytest.raises(ValidationError):
                pain_score.clean()


class ImagingRequestViewSetTest(APITestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.student_group, created = Group.objects.get_or_create(
            name=Role.STUDENT.value,
        )
        cls.user = get_user_model().objects.create_user(
            username="student1",
            password="testpass123",
        )
        cls.user.groups.add(cls.student_group)
        cls.patient = Patient.objects.create(
            first_name="John",
            last_name="Doe",
            date_of_birth="1990-01-01",
            mrn="MRN_SG_012",
            ward="Ward SG",
            bed="Bed 12",
            email="john.doe@example.com",
        )

    def setUp(self) -> None:
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_student_can_create_imaging_request(self) -> None:
        """Test that students can create imaging requests"""
        data = {
            "patient": self.patient.id,
            "test_type": "X-ray",
            "details": "Routine check-up for patient symptoms",
            "infection_control_precautions": "None",
            "imaging_focus": "Chest",
            "name": "Test X-Ray Request",
            "role": "Student",
        }
        response = self.client.post("/api/student-groups/imaging-requests/", data)
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["test_type"] == "X-ray"
        assert response.data["details"] == "Routine check-up for patient symptoms"
        assert response.data["role"] == "Student"

    def test_student_can_list_own_imaging_requests(self) -> None:
        """Test that students can only see their own imaging requests"""
        from student_groups.models import ImagingRequest

        ImagingRequest.objects.create(
            patient=self.patient,
            user=self.user,
            test_type="X-ray",
            details="Routine X-ray test",
            infection_control_precautions=ImagingRequest.InfectionControlPrecaution.NONE,
            imaging_focus="Arm",
            name="Test X-Ray",
            role="Medical Student",
        )
        # Create an imaging request for another user
        other_user = get_user_model().objects.create_user(
            username="student2",
            password="testpass123",
        )
        ImagingRequest.objects.create(
            patient=self.patient,
            user=other_user,
            test_type="CT scan",
            details="Routine CT scan test",
            infection_control_precautions=ImagingRequest.InfectionControlPrecaution.NONE,
            imaging_focus="Head",
            name="Test CT Scan",
            role="Medical Student",
        )

        # Students should only see their own imaging requests
        response = self.client.get("/api/student-groups/imaging-requests/")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 1
        assert response.data["results"][0]["test_type"] == "X-ray"
        # Note: 'user' field is hidden in student read view by the serializer

    def test_student_cannot_update_imaging_request(self) -> None:
        """Test that students cannot update imaging requests (only create and read)"""
        from student_groups.models import ImagingRequest

        imaging_request = ImagingRequest.objects.create(
            patient=self.patient,
            user=self.user,
            test_type="X-ray",
            details="Testing update permissions",
            infection_control_precautions=ImagingRequest.InfectionControlPrecaution.NONE,
            imaging_focus="Leg",
            name="Test Update Request",
            role="Medical Student",
        )

        data = {"status": "completed"}
        response = self.client.patch(
            f"/api/student-groups/imaging-requests/{imaging_request.id}/",
            data,
        )
        # Students don't have PATCH permission in LabRequestPermission, so returns 403
        # (Previously returned 405 because ViewSet lacks UpdateModelMixin, but permission check happens first)
        assert response.status_code == status.HTTP_403_FORBIDDEN


class PainScoreViewSetTest(APITestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.student_group, created = Group.objects.get_or_create(
            name=Role.STUDENT.value,
        )
        cls.user = get_user_model().objects.create_user(
            username="testuser",
            password="password",
        )
        cls.user.groups.add(cls.student_group)
        cls.patient = Patient.objects.create(
            first_name="John",
            last_name="Doe",
            date_of_birth="1990-01-01",
            mrn="MRN_SG_013",
            ward="Ward SG",
            bed="Bed 13",
            email="john.doe@example.com",
        )

    def setUp(self) -> None:
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_create_pain_score(self) -> None:
        data = {"patient": self.patient.id, "user": self.user.id, "score": 6}
        response = self.client.post(
            "/api/student-groups/observations/pain-scores/",
            data,
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert PainScore.objects.count() == 1
        pain_score = PainScore.objects.first()
        assert pain_score.score == 6
        assert pain_score.patient == self.patient
        assert pain_score.user == self.user

    def test_create_pain_score_invalid_range(self) -> None:
        # Test score above 10
        data = {"patient": self.patient.id, "user": self.user.id, "score": 15}
        response = self.client.post(
            "/api/student-groups/observations/pain-scores/",
            data,
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

        # Test negative score
        data["score"] = -2
        response = self.client.post(
            "/api/student-groups/observations/pain-scores/",
            data,
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_list_pain_scores(self) -> None:
        PainScore.objects.create(patient=self.patient, user=self.user, score=8)
        response = self.client.get("/api/student-groups/observations/pain-scores/")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 1
        assert response.data["results"][0]["score"] == 8
