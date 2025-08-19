from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from patients.models import Patient
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from student_groups.models import (
    BloodPressure,
    BodyTemperature,
    HeartRate,
    Note,
    ObservationManager,
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
            email="john.doe@example.com",
        )

    def test_create_note(self):
        note = Note.objects.create(
            patient=self.patient, user=self.user, content="This is a test note."
        )
        self.assertEqual(note.patient, self.patient)
        self.assertEqual(note.user, self.user)
        self.assertEqual(note.content, "This is a test note.")
        self.assertIsNotNone(note.created_at)
        self.assertIsNotNone(note.updated_at)
        self.assertEqual(
            str(note),
            f"{self.patient} - This is a test note.... ({self.user.username})",
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
            email="john.doe@example.com",
        )
        BloodPressure.objects.create(
            patient=cls.patient, user=cls.user, systolic=120, diastolic=80
        )
        HeartRate.objects.create(patient=cls.patient, user=cls.user, heart_rate=72)
        BodyTemperature.objects.create(
            patient=cls.patient, user=cls.user, temperature="36.6"
        )

    def test_get_observations_by_user_and_patient(self):
        observations = ObservationManager.get_observations_by_user_and_patient(
            self.user.id, self.patient.id
        )
        self.assertIn("blood_pressures", observations)
        self.assertIn("heart_rates", observations)
        self.assertIn("body_temperatures", observations)

        self.assertEqual(observations["blood_pressures"].count(), 1)
        self.assertEqual(observations["heart_rates"].count(), 1)
        self.assertEqual(observations["body_temperatures"].count(), 1)
        self.assertEqual(observations["blood_pressures"].first().systolic, 120)
        self.assertEqual(observations["heart_rates"].first().heart_rate, 72)
        self.assertEqual(
            observations["body_temperatures"].first().temperature, Decimal("36.6")
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
        }
        BloodPressure.objects.all().delete()
        HeartRate.objects.all().delete()

        created_instances = ObservationManager.create_observations(observation_data)

        self.assertEqual(BloodPressure.objects.count(), 1)
        self.assertEqual(HeartRate.objects.count(), 1)
        self.assertEqual(BodyTemperature.objects.count(), 1)

        self.assertIn("blood_pressure", created_instances)
        self.assertIn("heart_rate", created_instances)
        self.assertNotIn("body_temperature", created_instances)

        bp = BloodPressure.objects.first()
        self.assertEqual(bp.systolic, 130)
        self.assertEqual(bp.diastolic, 85)

        hr = HeartRate.objects.first()
        self.assertEqual(hr.heart_rate, 80)


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
            email="john.doe@example.com",
        )
        cls.note_data = {
            "patient": cls.patient.id,
            "user": cls.user.id,
            "content": "This is a test note.",
        }

    def test_note_serializer_valid(self):
        serializer = NoteSerializer(data=self.note_data)
        self.assertTrue(serializer.is_valid())

    def test_note_serializer_invalid(self):
        invalid_data = self.note_data.copy()
        invalid_data["content"] = ""
        serializer = NoteSerializer(data=invalid_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("content", serializer.errors)


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
        }

    def test_observations_serializer_valid(self):
        serializer = ObservationsSerializer(data=self.observation_data)
        self.assertTrue(serializer.is_valid(raise_exception=True))

    def test_observations_serializer_create(self):
        serializer = ObservationsSerializer(data=self.observation_data)
        self.assertTrue(serializer.is_valid(raise_exception=True))
        created_objects = serializer.save()
        self.assertEqual(len(created_objects), 3)
        self.assertIn("blood_pressure", created_objects)
        self.assertIn("heart_rate", created_objects)
        self.assertIn("body_temperature", created_objects)

    def test_observations_serializer_invalid_data(self):
        invalid_data = self.observation_data.copy()
        invalid_data["blood_pressure"]["systolic"] = "invalid"
        serializer = ObservationsSerializer(data=invalid_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("blood_pressure", serializer.errors)


class NoteViewSetTest(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            username="testuser", password="password"
        )
        self.patient = Patient.objects.create(
            first_name="John",
            last_name="Doe",
            date_of_birth="1990-01-01",
            email="john.doe@example.com",
        )
        self.note = Note.objects.create(
            patient=self.patient, user=self.user, content="Test note"
        )
        self.client.force_authenticate(user=self.user)

    def test_list_notes(self):
        response = self.client.get(reverse("note-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)

    def test_create_note(self):
        data = {
            "patient": self.patient.id,
            "user": self.user.id,
            "content": "New test note",
        }
        response = self.client.post(reverse("note-list"), data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Note.objects.count(), 2)

    def test_retrieve_note(self):
        response = self.client.get(reverse("note-detail", args=[self.note.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["content"], "Test note")

    def test_update_note(self):
        data = {"content": "Updated test note"}
        response = self.client.patch(
            reverse("note-detail", args=[self.note.id]), data, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.note.refresh_from_db()
        self.assertEqual(self.note.content, "Updated test note")

    def test_delete_note(self):
        response = self.client.delete(reverse("note-detail", args=[self.note.id]))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Note.objects.count(), 0)


class ObservationsViewSetTest(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            username="testuser", password="password"
        )
        self.patient = Patient.objects.create(
            first_name="John",
            last_name="Doe",
            date_of_birth="1990-01-01",
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
        }

    def test_create_observations(self):
        response = self.client.post(
            reverse("observation-list"), self.observation_data, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(BloodPressure.objects.count(), 1)
        self.assertEqual(HeartRate.objects.count(), 1)
        self.assertIn("blood_pressure", response.data)
        self.assertIn("heart_rate", response.data)

    def test_list_observations(self):
        BloodPressure.objects.create(
            patient=self.patient, user=self.user, systolic=120, diastolic=80
        )
        response = self.client.get(
            reverse("observation-list"),
            {"user": self.user.id, "patient": self.patient.id},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["blood_pressures"]), 1)
        self.assertEqual(len(response.data["heart_rates"]), 0)
