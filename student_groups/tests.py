from copy import deepcopy

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from core.cache import CacheManager
from core.context import Role
from patients.models import Patient
from student_groups.models import (
    BloodPressure,
    BloodSugar,
    BloodTestRequest,
    HeartRate,
    ImagingRequest,
    ObservationManager,
    PainScore,
    RespiratoryRate,
)
from student_groups.serializers import NoteSerializer
from student_groups.validators import ObservationValidator


class RoleFixtureMixin:
    """Reusable helpers for creating role-aware users and patients."""

    DEFAULT_PASSWORD = "test123"  # noqa: S105 - shared test credential

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
    def create_user(cls, username: str, role: Role | str):
        user = get_user_model().objects.create_user(
            username=username,
            password=cls.DEFAULT_PASSWORD,
        )
        role_value = role.value if isinstance(role, Role) else role
        user.groups.add(cls.role_groups[role_value])
        return user

    @classmethod
    def create_patient(cls, **overrides):
        defaults = {
            "first_name": "Test",
            "last_name": "Patient",
            "date_of_birth": "1990-01-01",
            "gender": Patient.Gender.UNSPECIFIED,
            "mrn": overrides.get(
                "mrn", f"MRN_SG_{get_user_model().objects.count():04d}"
            ),
            "ward": overrides.get("ward", "Ward SG"),
            "bed": overrides.get("bed", "Bed 1"),
            "phone_number": overrides.get("phone_number", "+61123456789"),
        }
        defaults.update(overrides)
        return Patient.objects.create(**defaults)


class ObservationValidatorTest(RoleFixtureMixin, TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()
        cls.patient = cls.create_patient(mrn="MRN_VAL_001")
        cls.user = cls.create_user("validator_student", Role.STUDENT)

    def test_blood_pressure_disallows_inverted_values(self) -> None:
        with self.assertRaises(ValidationError):
            ObservationValidator.validate_blood_pressure(
                self.patient,
                self.user,
                systolic=85,
                diastolic=120,
            )

    def test_body_temperature_requires_numeric_value(self) -> None:
        with self.assertRaises(ValidationError):
            ObservationValidator.validate_body_temperature(
                self.patient,
                self.user,
                temperature="high",
            )

    def test_body_temperature_enforces_range(self) -> None:
        with self.assertRaises(ValidationError):
            ObservationValidator.validate_body_temperature(
                self.patient,
                self.user,
                temperature=50,
            )

    def test_oxygen_saturation_bounds(self) -> None:
        with self.assertRaises(ValidationError):
            ObservationValidator.validate_oxygen_saturation(
                self.patient,
                self.user,
                saturation_percentage=30,
            )

    def test_pain_score_bounds(self) -> None:
        with self.assertRaises(ValidationError):
            ObservationValidator.validate_pain_score(
                self.patient,
                self.user,
                score=11,
            )


class ObservationManagerTest(RoleFixtureMixin, TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()
        cls.patient = cls.create_patient(mrn="MRN_MGR_001")
        cls.user = cls.create_user("manager_student", Role.STUDENT)
        cls.valid_payload = {
            "blood_pressure": {
                "patient": cls.patient,
                "user": cls.user,
                "systolic": 120,
                "diastolic": 80,
            },
            "heart_rate": {
                "patient": cls.patient,
                "user": cls.user,
                "heart_rate": 72,
            },
            "respiratory_rate": {
                "patient": cls.patient,
                "user": cls.user,
                "respiratory_rate": 16,
            },
            "blood_sugar": {
                "patient": cls.patient,
                "user": cls.user,
                "sugar_level": 5.4,
            },
        }

    def tearDown(self) -> None:
        BloodPressure.objects.all().delete()
        HeartRate.objects.all().delete()
        RespiratoryRate.objects.all().delete()
        BloodSugar.objects.all().delete()

    def test_create_observations_persists_all_records(self) -> None:
        created = ObservationManager.create_observations(self.valid_payload)
        assert set(created) == {
            "blood_pressure",
            "heart_rate",
            "respiratory_rate",
            "blood_sugar",
        }
        assert BloodPressure.objects.filter(patient=self.patient).count() == 1
        assert HeartRate.objects.filter(patient=self.patient).count() == 1
        assert RespiratoryRate.objects.filter(patient=self.patient).count() == 1
        assert BloodSugar.objects.filter(patient=self.patient).count() == 1

    def test_transaction_rolls_back_on_validation_error(self) -> None:
        invalid_payload = deepcopy(self.valid_payload)
        invalid_payload["blood_pressure"]["systolic"] = 60
        invalid_payload["blood_pressure"]["diastolic"] = 90

        with self.assertRaises(ValidationError):
            ObservationManager.create_observations(invalid_payload)

        assert BloodPressure.objects.count() == 0
        assert HeartRate.objects.count() == 0
        assert RespiratoryRate.objects.count() == 0
        assert BloodSugar.objects.count() == 0

    def test_get_observations_filters_by_user_and_patient(self) -> None:
        ObservationManager.create_observations(self.valid_payload)
        other_patient = self.create_patient(mrn="MRN_MGR_002")
        other_user = self.create_user("manager_other", Role.STUDENT)
        ObservationManager.create_observations({
            "blood_pressure": {
                "patient": other_patient,
                "user": other_user,
                "systolic": 130,
                "diastolic": 85,
            }
        })

        observations = ObservationManager.get_observations_by_user_and_patient(
            self.user.id,
            self.patient.id,
        )
        assert observations["blood_pressures"].count() == 1
        assert observations["blood_pressures"].first().user == self.user
        assert observations["blood_pressures"].first().patient == self.patient
        assert observations["heart_rates"].count() == 1
        assert observations["respiratory_rates"].count() == 1
        assert observations["blood_sugars"].count() == 1


class ObservationsViewSetTest(RoleFixtureMixin, APITestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()
        cls.student = cls.create_user("obs_student", Role.STUDENT)
        cls.other_student = cls.create_user("obs_other", Role.STUDENT)
        cls.patient = cls.create_patient(mrn="MRN_OBS_001")
        cls.other_patient = cls.create_patient(mrn="MRN_OBS_002")

    def setUp(self) -> None:
        self.client = APIClient()
        self.client.force_authenticate(self.student)
        CacheManager.invalidate_cache("student_groups:observations:list:*")

    def test_list_requires_patient_parameter(self) -> None:
        response = self.client.get("/api/student-groups/observations/")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["detail"] == "patient is required"

    def test_list_returns_only_current_user_records(self) -> None:
        BloodPressure.objects.create(
            patient=self.patient,
            user=self.student,
            systolic=120,
            diastolic=80,
        )
        BloodPressure.objects.create(
            patient=self.patient,
            user=self.other_student,
            systolic=140,
            diastolic=90,
        )
        HeartRate.objects.create(
            patient=self.patient,
            user=self.student,
            heart_rate=72,
        )
        RespiratoryRate.objects.create(
            patient=self.other_patient,
            user=self.student,
            respiratory_rate=20,
        )

        response = self.client.get(
            "/api/student-groups/observations/",
            {"patient": self.patient.id},
        )
        assert response.status_code == status.HTTP_200_OK
        results = response.data["results"]
        assert len(results["blood_pressures"]) == 1
        assert results["blood_pressures"][0]["systolic"] == 120
        assert len(results["heart_rates"]) == 1
        # Observation for other patient should be filtered out
        assert len(results["respiratory_rates"]) == 0

    def test_list_respects_page_size_per_observation(self) -> None:
        BloodPressure.objects.all().delete()
        for systolic in (120, 130, 140):
            BloodPressure.objects.create(
                patient=self.patient,
                user=self.student,
                systolic=systolic,
                diastolic=80,
            )

        response = self.client.get(
            "/api/student-groups/observations/",
            {"patient": self.patient.id, "page_size": 1},
        )
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]["blood_pressures"]) == 1

        response_invalid = self.client.get(
            "/api/student-groups/observations/",
            {"patient": self.patient.id, "page_size": "invalid"},
        )
        assert response_invalid.status_code == status.HTTP_200_OK
        assert len(response_invalid.data["results"]["blood_pressures"]) == 3


class InvestigationRequestRBACIntegrationTest(RoleFixtureMixin, APITestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()
        cls.student = cls.create_user("rbac_student", Role.STUDENT)
        cls.other_student = cls.create_user("rbac_other", Role.STUDENT)
        cls.instructor = cls.create_user("rbac_instructor", Role.INSTRUCTOR)
        cls.patient = cls.create_patient(mrn="MRN_REQ_001")

    def setUp(self) -> None:
        self.client = APIClient()

    def test_student_can_only_see_own_imaging_requests(self) -> None:
        ImagingRequest.objects.create(
            patient=self.patient,
            user=self.student,
            test_type="X-ray",
            details="Chest pain",
            infection_control_precautions=ImagingRequest.InfectionControlPrecaution.NONE,
            imaging_focus="Chest",
            name="Student request",
            role="Medical Student",
        )
        ImagingRequest.objects.create(
            patient=self.patient,
            user=self.other_student,
            test_type="MRI",
            details="Other student",
            infection_control_precautions=ImagingRequest.InfectionControlPrecaution.NONE,
            imaging_focus="Head",
            name="Other request",
            role="Medical Student",
        )

        self.client.force_authenticate(self.student)
        response = self.client.get("/api/student-groups/imaging-requests/")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 1
        assert response.data["results"][0]["test_type"] == "X-ray"

    def test_student_cannot_update_their_imaging_request(self) -> None:
        request_obj = ImagingRequest.objects.create(
            patient=self.patient,
            user=self.student,
            test_type="CT",
            details="Original",
            infection_control_precautions=ImagingRequest.InfectionControlPrecaution.NONE,
            imaging_focus="Abdomen",
            name="Update attempt",
            role="Medical Student",
        )

        self.client.force_authenticate(self.student)
        response = self.client.patch(
            f"/api/student-groups/imaging-requests/{request_obj.id}/",
            {"details": "Updated"},
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_instructor_can_filter_by_user(self) -> None:
        ImagingRequest.objects.create(
            patient=self.patient,
            user=self.student,
            test_type="X-ray",
            details="Filter me",
            infection_control_precautions=ImagingRequest.InfectionControlPrecaution.NONE,
            imaging_focus="Chest",
            name="Filter",
            role="Medical Student",
        )
        ImagingRequest.objects.create(
            patient=self.patient,
            user=self.other_student,
            test_type="MRI",
            details="Other",
            infection_control_precautions=ImagingRequest.InfectionControlPrecaution.NONE,
            imaging_focus="Head",
            name="Other",
            role="Medical Student",
        )

        self.client.force_authenticate(self.instructor)
        response = self.client.get(
            "/api/student-groups/imaging-requests/",
            {"user": self.student.id},
        )
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 1

        bad_response = self.client.get(
            "/api/student-groups/imaging-requests/",
            {"user": "invalid"},
        )
        assert bad_response.status_code == status.HTTP_400_BAD_REQUEST
        assert "user" in bad_response.data

    def test_invalid_patient_query_returns_error(self) -> None:
        self.client.force_authenticate(self.instructor)
        response = self.client.get(
            "/api/student-groups/imaging-requests/",
            {"patient": "invalid"},
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "patient" in response.data

    def test_student_cannot_delete_another_students_blood_request(self) -> None:
        request_obj = BloodTestRequest.objects.create(
            patient=self.patient,
            user=self.other_student,
            test_type=BloodTestRequest.TestType.FBC,
            details="Other student's request",
            name="Other blood",
            role="Medical Student",
        )

        self.client.force_authenticate(self.student)
        response = self.client.delete(
            f"/api/student-groups/blood-test-requests/{request_obj.id}/",
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert BloodTestRequest.objects.filter(id=request_obj.id).exists()


class PainScoreApiValidationTest(RoleFixtureMixin, APITestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()
        cls.student = cls.create_user("pain_student", Role.STUDENT)
        cls.patient = cls.create_patient(mrn="MRN_PAIN_001")

    def setUp(self) -> None:
        self.client = APIClient()
        self.client.force_authenticate(self.student)

    def test_rejects_out_of_range_scores(self) -> None:
        for score in (-1, 12):
            response = self.client.post(
                "/api/student-groups/observations/pain-scores/",
                {"patient": self.patient.id, "score": score},
            )
            assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_accepts_valid_score(self) -> None:
        response = self.client.post(
            "/api/student-groups/observations/pain-scores/",
            {"patient": self.patient.id, "score": 4},
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert PainScore.objects.filter(patient=self.patient, score=4).exists()


class NoteSerializerValidationTest(RoleFixtureMixin, TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()
        cls.patient = cls.create_patient(mrn="MRN_NOTE_001")
        cls.student = cls.create_user("note_student", Role.STUDENT)

    def test_serializer_enforces_required_fields(self) -> None:
        serializer = NoteSerializer(
            data={
                "patient": self.patient.id,
                "user": self.student.id,
                "name": "",
                "role": "Medical Student",
                "content": "",
            }
        )
        assert not serializer.is_valid()
        assert set(serializer.errors) >= {"name", "content"}

    def test_serializer_accepts_complete_payload(self) -> None:
        serializer = NoteSerializer(
            data={
                "patient": self.patient.id,
                "user": self.student.id,
                "name": "Dr. House",
                "role": "Medical Student",
                "content": "Patient improving.",
            }
        )
        assert serializer.is_valid(raise_exception=True)
