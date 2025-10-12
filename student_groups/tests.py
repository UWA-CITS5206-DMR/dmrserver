from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from patients.models import Patient
from rest_framework import status
from rest_framework.test import APIClient, APITestCase
from core.context import Role

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
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(
            username="testuser", password="password"
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

    def test_create_note(self):
        note = Note.objects.create(
            patient=self.patient,
            user=self.user,
            name="Dr. Smith",
            role="Doctor",
            content="This is a test note.",
        )
        self.assertEqual(note.patient, self.patient)
        self.assertEqual(note.user, self.user)
        self.assertEqual(note.name, "Dr. Smith")
        self.assertEqual(note.role, "Doctor")
        self.assertEqual(note.content, "This is a test note.")
        self.assertIsNotNone(note.created_at)
        self.assertIsNotNone(note.updated_at)
        self.assertEqual(
            str(note), f"Note for {self.patient} by Dr. Smith ({self.user.username})"
        )


class BloodPressureModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(
            username="testuser", password="password"
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

    def test_create_blood_pressure(self):
        blood_pressure = BloodPressure.objects.create(
            patient=self.patient, user=self.user, systolic=120, diastolic=80
        )
        self.assertEqual(blood_pressure.patient, self.patient)
        self.assertEqual(blood_pressure.user, self.user)
        self.assertEqual(blood_pressure.systolic, 120)
        self.assertEqual(blood_pressure.diastolic, 80)
        self.assertIsNotNone(blood_pressure.created_at)
        self.assertEqual(
            str(blood_pressure), f"{self.patient} - 120/80 mmHg ({self.user.username})"
        )


class HeartRateModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(
            username="testuser", password="password"
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

    def test_create_heart_rate(self):
        heart_rate = HeartRate.objects.create(
            patient=self.patient, user=self.user, heart_rate=72
        )
        self.assertEqual(heart_rate.patient, self.patient)
        self.assertEqual(heart_rate.user, self.user)
        self.assertEqual(heart_rate.heart_rate, 72)
        self.assertIsNotNone(heart_rate.created_at)
        self.assertEqual(
            str(heart_rate), f"{self.patient} - 72 bpm ({self.user.username})"
        )


class BodyTemperatureModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(
            username="testuser", password="password"
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

    def test_create_body_temperature(self):
        body_temperature = BodyTemperature.objects.create(
            patient=self.patient, user=self.user, temperature=Decimal("36.6")
        )
        self.assertEqual(body_temperature.patient, self.patient)
        self.assertEqual(body_temperature.user, self.user)
        self.assertEqual(body_temperature.temperature, Decimal("36.6"))
        self.assertIsNotNone(body_temperature.created_at)
        self.assertEqual(
            str(body_temperature), f"{self.patient} - 36.6°C ({self.user.username})"
        )

    def test_body_temperature_validation(self):
        with self.assertRaises(ValidationError):
            BodyTemperature.objects.create(
                patient=self.patient, user=self.user, temperature="50.0"
            )


class ObservationManagerTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(
            username="testuser", password="password"
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
            patient=cls.patient, user=cls.user, systolic=120, diastolic=80
        )
        HeartRate.objects.create(patient=cls.patient, user=cls.user, heart_rate=72)
        BodyTemperature.objects.create(
            patient=cls.patient, user=cls.user, temperature="36.6"
        )
        RespiratoryRate.objects.create(
            patient=cls.patient, user=cls.user, respiratory_rate=16
        )
        BloodSugar.objects.create(
            patient=cls.patient, user=cls.user, sugar_level="100.0"
        )
        OxygenSaturation.objects.create(
            patient=cls.patient, user=cls.user, saturation_percentage=98
        )

    def test_get_observations_by_user_and_patient(self):
        observations = ObservationManager.get_observations_by_user_and_patient(
            self.user.id, self.patient.id
        )
        self.assertIn("blood_pressures", observations)
        self.assertIn("heart_rates", observations)
        self.assertIn("body_temperatures", observations)
        self.assertIn("respiratory_rates", observations)
        self.assertIn("blood_sugars", observations)
        self.assertIn("oxygen_saturations", observations)

        self.assertEqual(observations["blood_pressures"].count(), 1)
        self.assertEqual(observations["heart_rates"].count(), 1)
        self.assertEqual(observations["body_temperatures"].count(), 1)
        self.assertEqual(observations["respiratory_rates"].count(), 1)
        self.assertEqual(observations["blood_sugars"].count(), 1)
        self.assertEqual(observations["oxygen_saturations"].count(), 1)
        self.assertEqual(observations["blood_pressures"].first().systolic, 120)
        self.assertEqual(observations["heart_rates"].first().heart_rate, 72)
        self.assertEqual(
            observations["body_temperatures"].first().temperature, Decimal("36.6")
        )
        self.assertEqual(observations["respiratory_rates"].first().respiratory_rate, 16)
        self.assertEqual(
            observations["blood_sugars"].first().sugar_level, Decimal("100.0")
        )
        self.assertEqual(
            observations["oxygen_saturations"].first().saturation_percentage, 98
        )

    def test_create_observations(self):
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

        self.assertEqual(BloodPressure.objects.count(), 1)
        self.assertEqual(HeartRate.objects.count(), 1)
        self.assertEqual(BodyTemperature.objects.count(), 0)
        self.assertEqual(RespiratoryRate.objects.count(), 1)
        self.assertEqual(BloodSugar.objects.count(), 1)
        self.assertEqual(OxygenSaturation.objects.count(), 1)

        self.assertIn("blood_pressure", created_instances)
        self.assertIn("heart_rate", created_instances)
        self.assertNotIn("body_temperature", created_instances)
        self.assertIn("respiratory_rate", created_instances)
        self.assertIn("blood_sugar", created_instances)
        self.assertIn("oxygen_saturation", created_instances)

        bp = BloodPressure.objects.first()
        self.assertEqual(bp.systolic, 130)
        self.assertEqual(bp.diastolic, 85)

        hr = HeartRate.objects.first()
        self.assertEqual(hr.heart_rate, 80)

        rr = RespiratoryRate.objects.first()
        self.assertEqual(rr.respiratory_rate, 18)

        bs = BloodSugar.objects.first()
        self.assertEqual(bs.sugar_level, Decimal("110.0"))

        os = OxygenSaturation.objects.first()
        self.assertEqual(os.saturation_percentage, 97)


class NoteSerializerTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(
            username="testuser", password="password"
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

    def test_note_serializer_valid(self):
        serializer = NoteSerializer(data=self.note_data)
        self.assertTrue(serializer.is_valid(raise_exception=True))

    def test_note_serializer_invalid_no_content(self):
        invalid_data = self.note_data.copy()
        invalid_data["content"] = ""
        serializer = NoteSerializer(data=invalid_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("content", serializer.errors)

    def test_note_serializer_invalid_no_name(self):
        invalid_data = self.note_data.copy()
        invalid_data["name"] = ""
        serializer = NoteSerializer(data=invalid_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("name", serializer.errors)


class ObservationsSerializerTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(
            username="testuser", password="password"
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

    def test_observations_serializer_valid(self):
        serializer = ObservationsSerializer(data=self.observation_data)
        self.assertTrue(serializer.is_valid(raise_exception=True))

    def test_observations_serializer_create(self):
        serializer = ObservationsSerializer(data=self.observation_data)
        self.assertTrue(serializer.is_valid(raise_exception=True))
        created_objects = serializer.save()
        self.assertEqual(len(created_objects), 6)
        self.assertIn("blood_pressure", created_objects)
        self.assertIn("heart_rate", created_objects)
        self.assertIn("body_temperature", created_objects)
        self.assertIn("respiratory_rate", created_objects)
        self.assertIn("blood_sugar", created_objects)
        self.assertIn("oxygen_saturation", created_objects)

    def test_observations_serializer_invalid_data(self):
        invalid_data = self.observation_data.copy()
        invalid_data["blood_pressure"]["systolic"] = "invalid"
        serializer = ObservationsSerializer(data=invalid_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("blood_pressure", serializer.errors)


class NoteViewSetTest(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.student_group, created = Group.objects.get_or_create(
            name=Role.STUDENT.value
        )
        self.user = get_user_model().objects.create_user(
            username="testuser", password="password"
        )
        self.user.groups.add(self.student_group)
        self.patient = Patient.objects.create(
            first_name="John",
            last_name="Doe",
            date_of_birth="1990-01-01",
            mrn="MRN400",
            ward="Ward G",
            bed="Bed 7",
            email="john.doe@example.com",
        )
        self.note = Note.objects.create(
            patient=self.patient,
            user=self.user,
            name="Dr. Smith",
            role="Doctor",
            content="Test note",
        )
        self.client.force_authenticate(user=self.user)

    def test_list_notes(self):
        response = self.client.get(reverse("note-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)

    def test_create_note(self):
        data = {
            "patient": self.patient.id,
            "name": "Dr. Jones",
            "role": "Doctor",
            "content": "New test note",
        }
        response = self.client.post(reverse("note-list"), data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Note.objects.count(), 2)
        self.assertEqual(response.data["name"], "Dr. Jones")

    def test_retrieve_note(self):
        response = self.client.get(reverse("note-detail", args=[self.note.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "Dr. Smith")
        self.assertEqual(response.data["content"], "Test note")

    def test_update_note(self):
        data = {"name": "Dr. Brown", "content": "Updated test note"}
        response = self.client.patch(
            reverse("note-detail", args=[self.note.id]), data, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.note.refresh_from_db()
        self.assertEqual(self.note.name, "Dr. Brown")
        self.assertEqual(self.note.content, "Updated test note")

    def test_delete_note(self):
        response = self.client.delete(reverse("note-detail", args=[self.note.id]))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Note.objects.count(), 0)


class ObservationsViewSetTest(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.student_group, created = Group.objects.get_or_create(
            name=Role.STUDENT.value
        )
        self.user = get_user_model().objects.create_user(
            username="testuser", password="password"
        )
        self.user.groups.add(self.student_group)
        self.patient = Patient.objects.create(
            first_name="John",
            last_name="Doe",
            date_of_birth="1990-01-01",
            mrn="MRN401",
            ward="Ward H",
            bed="Bed 8",
            email="john.doe@example.com",
        )
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

    def test_create_observations(self):
        response = self.client.post(
            reverse("observation-list"), self.observation_data, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(BloodPressure.objects.count(), 1)
        self.assertEqual(HeartRate.objects.count(), 1)
        self.assertEqual(RespiratoryRate.objects.count(), 1)
        self.assertEqual(PainScore.objects.count(), 1)
        self.assertIn("blood_pressure", response.data)
        self.assertIn("heart_rate", response.data)
        self.assertIn("respiratory_rate", response.data)
        self.assertIn("pain_score", response.data)

    def test_list_observations(self):
        BloodPressure.objects.create(
            patient=self.patient, user=self.user, systolic=120, diastolic=80
        )
        RespiratoryRate.objects.create(
            patient=self.patient, user=self.user, respiratory_rate=16
        )
        response = self.client.get(
            reverse("observation-list"),
            {"patient_id": self.patient.id},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Check pagination format
        self.assertIn("count", response.data)
        self.assertIn("next", response.data)
        self.assertIn("previous", response.data)
        self.assertIn("results", response.data)
        # Check observation data is in results
        self.assertEqual(len(response.data["results"]["blood_pressures"]), 1)
        self.assertEqual(len(response.data["results"]["heart_rates"]), 0)
        self.assertEqual(len(response.data["results"]["respiratory_rates"]), 1)

    def test_list_observations_with_pagination(self):
        """Test that page_size parameter limits results for each observation type"""
        # Create multiple observations
        for i in range(5):
            BloodPressure.objects.create(
                patient=self.patient, user=self.user, systolic=120 + i, diastolic=80 + i
            )
            HeartRate.objects.create(
                patient=self.patient, user=self.user, heart_rate=70 + i
            )

        # Test with page_size=2
        response = self.client.get(
            reverse("observation-list"),
            {"patient_id": self.patient.id, "page_size": 2},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Check pagination format
        self.assertIn("count", response.data)
        self.assertIn("results", response.data)
        self.assertEqual(len(response.data["results"]["blood_pressures"]), 2)
        self.assertEqual(len(response.data["results"]["heart_rates"]), 2)

        # Test with page_size=1
        response = self.client.get(
            reverse("observation-list"),
            {"patient_id": self.patient.id, "page_size": 1},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("count", response.data)
        self.assertIn("results", response.data)
        self.assertEqual(len(response.data["results"]["blood_pressures"]), 1)
        self.assertEqual(len(response.data["results"]["heart_rates"]), 1)

    def test_list_observations_with_ordering(self):
        """Test that ordering parameter sorts results correctly"""
        import time

        # Create observations with slight time differences
        BloodPressure.objects.create(
            patient=self.patient, user=self.user, systolic=120, diastolic=80
        )
        time.sleep(0.01)  # Ensure different timestamps
        BloodPressure.objects.create(
            patient=self.patient, user=self.user, systolic=130, diastolic=85
        )

        # Test descending order (newest first) - default
        response = self.client.get(
            reverse("observation-list"),
            {"patient_id": self.patient.id, "ordering": "-created_at"},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("results", response.data)
        self.assertEqual(
            response.data["results"]["blood_pressures"][0]["systolic"], 130
        )  # Newest first

        # Test ascending order (oldest first)
        response = self.client.get(
            reverse("observation-list"),
            {"patient_id": self.patient.id, "ordering": "created_at"},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("results", response.data)
        self.assertEqual(
            response.data["results"]["blood_pressures"][0]["systolic"], 120
        )  # Oldest first


class RespiratoryRateModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(
            username="testuser", password="password"
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

    def test_create_respiratory_rate(self):
        respiratory_rate = RespiratoryRate.objects.create(
            patient=self.patient, user=self.user, respiratory_rate=16
        )
        self.assertEqual(respiratory_rate.patient, self.patient)
        self.assertEqual(respiratory_rate.user, self.user)
        self.assertEqual(respiratory_rate.respiratory_rate, 16)
        self.assertIsNotNone(respiratory_rate.created_at)
        self.assertEqual(
            str(respiratory_rate),
            f"{self.patient} - 16 breaths/min ({self.user.username})",
        )


class BloodSugarModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(
            username="testuser", password="password"
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

    def test_create_blood_sugar(self):
        blood_sugar = BloodSugar.objects.create(
            patient=self.patient, user=self.user, sugar_level=Decimal("99.5")
        )
        self.assertEqual(blood_sugar.patient, self.patient)
        self.assertEqual(blood_sugar.user, self.user)
        self.assertEqual(blood_sugar.sugar_level, Decimal("99.5"))
        self.assertIsNotNone(blood_sugar.created_at)
        self.assertEqual(
            str(blood_sugar), f"{self.patient} - 99.5 mg/dL ({self.user.username})"
        )


class OxygenSaturationModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(
            username="testuser", password="password"
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

    def test_create_oxygen_saturation(self):
        oxygen_saturation = OxygenSaturation.objects.create(
            patient=self.patient, user=self.user, saturation_percentage=98
        )
        self.assertEqual(oxygen_saturation.patient, self.patient)
        self.assertEqual(oxygen_saturation.user, self.user)
        self.assertEqual(oxygen_saturation.saturation_percentage, 98)
        self.assertIsNotNone(oxygen_saturation.created_at)
        self.assertEqual(
            str(oxygen_saturation), f"{self.patient} - 98% ({self.user.username})"
        )


class PainScoreModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(
            username="testuser", password="password"
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

    def test_create_pain_score(self):
        pain_score = PainScore.objects.create(
            patient=self.patient, user=self.user, score=7
        )
        self.assertEqual(pain_score.patient, self.patient)
        self.assertEqual(pain_score.user, self.user)
        self.assertEqual(pain_score.score, 7)
        self.assertIsNotNone(pain_score.created_at)
        self.assertEqual(
            str(pain_score), f"{self.patient} - Pain 7/10 ({self.user.username})"
        )

    def test_pain_score_validation_valid_range(self):
        # Test valid range 0-10
        for score in [0, 5, 10]:
            pain_score = PainScore(patient=self.patient, user=self.user, score=score)
            try:
                pain_score.clean()
                pain_score.save()
                self.assertEqual(pain_score.score, score)
            except ValidationError:
                self.fail(f"ValidationError raised for valid score {score}")

    def test_pain_score_validation_invalid_range(self):
        # Test invalid scores
        for score in [-1, 11, 15]:
            pain_score = PainScore(patient=self.patient, user=self.user, score=score)
            with self.assertRaises(ValidationError):
                pain_score.clean()


class ImagingRequestViewSetTest(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.student_group, created = Group.objects.get_or_create(
            name=Role.STUDENT.value
        )
        self.user = get_user_model().objects.create_user(
            username="student1", password="testpass123"
        )
        self.user.groups.add(self.student_group)
        self.patient = Patient.objects.create(
            first_name="John",
            last_name="Doe",
            date_of_birth="1990-01-01",
            mrn="MRN_SG_012",
            ward="Ward SG",
            bed="Bed 12",
            email="john.doe@example.com",
        )
        self.client.force_authenticate(user=self.user)

    def test_student_can_create_imaging_request(self):
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
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["test_type"], "X-ray")
        self.assertEqual(
            response.data["details"], "Routine check-up for patient symptoms"
        )
        self.assertEqual(response.data["role"], "Student")

    def test_student_can_list_own_imaging_requests(self):
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
            username="student2", password="testpass123"
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
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["test_type"], "X-ray")
        # Note: 'user' field is hidden in student read view by the serializer

    def test_student_cannot_update_imaging_request(self):
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
            f"/api/student-groups/imaging-requests/{imaging_request.id}/", data
        )
        # Students don't have PATCH permission in LabRequestPermission, so returns 403
        # (Previously returned 405 because ViewSet lacks UpdateModelMixin, but permission check happens first)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class PainScoreViewSetTest(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.student_group, created = Group.objects.get_or_create(
            name=Role.STUDENT.value
        )
        self.user = get_user_model().objects.create_user(
            username="testuser", password="password"
        )
        self.user.groups.add(self.student_group)
        self.patient = Patient.objects.create(
            first_name="John",
            last_name="Doe",
            date_of_birth="1990-01-01",
            mrn="MRN_SG_013",
            ward="Ward SG",
            bed="Bed 13",
            email="john.doe@example.com",
        )
        self.client.force_authenticate(user=self.user)

    def test_create_pain_score(self):
        data = {"patient": self.patient.id, "user": self.user.id, "score": 6}
        response = self.client.post(
            "/api/student-groups/observations/pain-scores/", data
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(PainScore.objects.count(), 1)
        pain_score = PainScore.objects.first()
        self.assertEqual(pain_score.score, 6)
        self.assertEqual(pain_score.patient, self.patient)
        self.assertEqual(pain_score.user, self.user)

    def test_create_pain_score_invalid_range(self):
        # Test score above 10
        data = {"patient": self.patient.id, "user": self.user.id, "score": 15}
        response = self.client.post(
            "/api/student-groups/observations/pain-scores/", data
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Test negative score
        data["score"] = -2
        response = self.client.post(
            "/api/student-groups/observations/pain-scores/", data
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_list_pain_scores(self):
        PainScore.objects.create(patient=self.patient, user=self.user, score=8)
        response = self.client.get("/api/student-groups/observations/pain-scores/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["score"], 8)
