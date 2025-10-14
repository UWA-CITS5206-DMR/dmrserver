"""
Test Configuration for DMR Login Integration Tests

This module contains configuration settings and utilities for login testing.
"""

import os

import django
from django.conf import settings

# Test Configuration
TEST_CONFIG = {
    "BASE_URL": "http://127.0.0.1:8000",
    "TIMEOUT": 30,
    "MAX_RETRY_ATTEMPTS": 3,
    "RETRY_DELAY": 1,  # seconds
    # Test user credentials
    "TEST_USERS": {
        "doctor": {
            "username": "test_doctor",
            "password": "doctor_password_123",
            "email": "doctor@dmr-test.com",
            "first_name": "Dr. John",
            "last_name": "Smith",
            "role": "doctor",
        },
        "nurse": {
            "username": "test_nurse",
            "password": "nurse_password_123",
            "email": "nurse@dmr-test.com",
            "first_name": "Jane",
            "last_name": "Doe",
            "role": "nurse",
        },
        "admin": {
            "username": "test_admin",
            "password": "admin_password_123",
            "email": "admin@dmr-test.com",
            "is_staff": True,
            "is_superuser": True,
            "role": "admin",
        },
    },
    # Test endpoints
    "ENDPOINTS": {
        "login": "/api-auth/login/",
        "logout": "/api-auth/logout/",
        "patients": "/api/patients/",
        "notes": "/api/student-groups/notes/",
        "blood_pressure": "/api/student-groups/observations/blood-pressures/",
        "heart_rate": "/api/student-groups/observations/heart-rates/",
        "temperature": "/api/student-groups/observations/body-temperatures/",
        "admin": "/admin/",
        "swagger": "/schema/swagger-ui/",
    },
    # Test data
    "TEST_PATIENT": {
        "first_name": "John",
        "last_name": "TestPatient",
        "date_of_birth": "1990-01-01",
        "gender": "unspecified",
        "mrn": "MRN900",
        "ward": "Ward Test",
        "bed": "Bed T1",
        "email": "test_patient@dmr-test.com",
        "phone_number": "+1234567890",
    },
    "TEST_OBSERVATIONS": {
        "blood_pressure": {"systolic": 120, "diastolic": 80},
        "heart_rate": {"heart_rate": 72},
        "body_temperature": {"temperature": "36.5"},
    },
}


def setup_django_for_testing() -> None:
    """Setup Django environment for testing"""
    if not settings.configured:
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "dmr.settings")
        django.setup()


def get_test_user_credentials(role="doctor"):
    """Get test user credentials by role"""
    return TEST_CONFIG["TEST_USERS"].get(role, TEST_CONFIG["TEST_USERS"]["doctor"])


def get_endpoint_url(endpoint_name, base_url=None) -> str:
    """Get full URL for an endpoint"""
    if base_url is None:
        base_url = TEST_CONFIG["BASE_URL"]

    endpoint_path = TEST_CONFIG["ENDPOINTS"].get(endpoint_name, "")
    return f"{base_url.rstrip('/')}{endpoint_path}"


def get_test_data(data_type):
    """Get test data by type"""
    if data_type == "patient":
        return TEST_CONFIG["TEST_PATIENT"].copy()
    if data_type in TEST_CONFIG["TEST_OBSERVATIONS"]:
        return TEST_CONFIG["TEST_OBSERVATIONS"][data_type].copy()
    return {}


class TestDataManager:
    """Manages test data creation and cleanup"""

    def __init__(self) -> None:
        setup_django_for_testing()
        from django.contrib.auth.models import User

        from patients.models import Patient

        self.User = User
        self.Patient = Patient
        self.created_users = []
        self.created_patients = []

    def create_test_users(self):
        """Create all test users"""
        for role in TEST_CONFIG["TEST_USERS"]:
            user = self.create_test_user(role)
            if user:
                self.created_users.append(user)
        return self.created_users

    def create_test_user(self, role="doctor"):
        """Create a single test user"""
        user_data = get_test_user_credentials(role)

        # Check if user already exists
        if self.User.objects.filter(username=user_data["username"]).exists():
            return self.User.objects.get(username=user_data["username"])

        # Create new user
        user = self.User.objects.create_user(
            username=user_data["username"],
            email=user_data["email"],
            password=user_data["password"],
            first_name=user_data.get("first_name", ""),
            last_name=user_data.get("last_name", ""),
        )

        # Set admin privileges if needed
        if user_data.get("is_staff"):
            user.is_staff = True
        if user_data.get("is_superuser"):
            user.is_superuser = True
        user.save()

        return user

    def create_test_patient(self):
        """Create a test patient"""
        patient_data = get_test_data("patient")

        # Ensure unique MRN used for lookup if provided
        mrn = patient_data.get("mrn")
        if mrn and self.Patient.objects.filter(mrn=mrn).exists():
            return self.Patient.objects.get(mrn=mrn)

        # Remove email key if present (field removed)
        patient_data.pop("email", None)

        # Create new patient
        patient = self.Patient.objects.create(**patient_data)
        self.created_patients.append(patient)

        return patient

    def cleanup_test_data(self) -> None:
        """Clean up created test data"""
        # Note: Be careful with cleanup in production!
        for user in self.created_users:
            if user.username.startswith("test_"):
                user.delete()

        for patient in self.created_patients:
            # Prefer checking MRN or phone_number for test-created patients
            mrn = getattr(patient, "mrn", "") or ""
            phone = getattr(patient, "phone_number", "") or ""
            if "test" in mrn.lower() or "test" in phone.lower():
                patient.delete()


def run_test_setup():
    """Run complete test setup"""

    manager = TestDataManager()

    # Create test users
    manager.create_test_users()

    # Create test patient
    manager.create_test_patient()

    return manager


if __name__ == "__main__":
    # Run test setup when called directly
    manager = run_test_setup()

    # Optionally run cleanup (uncomment to enable)
    # import time
    # print("Waiting 5 seconds before cleanup...")
    # time.sleep(5)
    # manager.cleanup_test_data()
