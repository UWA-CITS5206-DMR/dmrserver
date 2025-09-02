# DMR Testing Guide

## Table of Contents
1. [Testing Overview](#testing-overview)
2. [Test Setup](#test-setup)
3. [Unit Testing](#unit-testing)
4. [API Testing](#api-testing)
5. [Integration Testing](#integration-testing)
6. [Test Data Management](#test-data-management)
7. [Coverage Analysis](#coverage-analysis)
8. [Performance Testing](#performance-testing)
9. [Manual Testing](#manual-testing)
10. [Continuous Integration](#continuous-integration)

## Testing Overview

The DMR project uses Django's built-in testing framework along with Django REST Framework's testing utilities. The testing strategy includes:

- **Unit Tests**: Test individual components in isolation
- **API Tests**: Test REST API endpoints and serializers
- **Integration Tests**: Test complete workflows
- **Performance Tests**: Test system under load
- **Manual Tests**: User acceptance testing

### Testing Philosophy
- **Test-Driven Development (TDD)**: Write tests before implementation
- **Comprehensive Coverage**: Aim for >90% code coverage
- **Fast Execution**: Tests should run quickly for frequent execution
- **Isolation**: Tests should not depend on each other
- **Realistic Data**: Use factory patterns for test data

## Test Setup

### Running Tests

#### Basic Test Execution
```bash
# Run all tests
./start.sh test

# Or directly with uv
uv run python manage.py test

# Run specific app tests
uv run python manage.py test patients
uv run python manage.py test student_groups

# Run specific test class
uv run python manage.py test patients.tests.PatientModelTests

# Run specific test method
uv run python manage.py test patients.tests.PatientModelTests.test_patient_creation
```

#### Verbose Test Output
```bash
# Run with verbose output
uv run python manage.py test --verbosity=2

# Keep test database after tests
uv run python manage.py test --keepdb

# Run tests in parallel
uv run python manage.py test --parallel
```

### Test Database Configuration

The test database is automatically created and destroyed for each test run:

```python
# settings.py - Test database settings
if 'test' in sys.argv:
    DATABASES['default'] = {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:'  # In-memory database for speed
    }
```

### Development Dependencies

Add testing tools to your development environment:

```bash
# Add testing dependencies
uv add --dev pytest pytest-django pytest-cov factory-boy
uv add --dev coverage django-coverage-plugin
```

## Unit Testing

### Model Testing

#### Patient Model Tests
```python
# patients/tests.py
from django.test import TestCase
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from .models import Patient, File
import tempfile
from django.core.files.uploadedfile import SimpleUploadedFile

class PatientModelTests(TestCase):
    def setUp(self):
        """Set up test data"""
        self.patient_data = {
            'first_name': 'John',
            'last_name': 'Doe',
            'date_of_birth': '1990-01-01',
            'email': 'john@example.com',
            'phone_number': '+1234567890'
        }

    def test_patient_creation(self):
        """Test basic patient creation"""
        patient = Patient.objects.create(**self.patient_data)
        self.assertEqual(patient.first_name, 'John')
        self.assertEqual(patient.last_name, 'Doe')
        self.assertEqual(str(patient), 'John Doe')
        self.assertTrue(patient.created_at)
        self.assertTrue(patient.updated_at)

    def test_email_uniqueness(self):
        """Test that email must be unique"""
        Patient.objects.create(**self.patient_data)
        
        # Try to create another patient with same email
        with self.assertRaises(IntegrityError):
            Patient.objects.create(**self.patient_data)

    def test_email_validation(self):
        """Test email format validation"""
        invalid_data = self.patient_data.copy()
        invalid_data['email'] = 'invalid-email'
        
        patient = Patient(**invalid_data)
        with self.assertRaises(ValidationError):
            patient.full_clean()

    def test_future_birth_date_validation(self):
        """Test that birth date cannot be in the future"""
        from datetime import date, timedelta
        
        future_data = self.patient_data.copy()
        future_data['date_of_birth'] = date.today() + timedelta(days=1)
        
        patient = Patient(**future_data)
        with self.assertRaises(ValidationError):
            patient.full_clean()

    def test_patient_str_representation(self):
        """Test string representation"""
        patient = Patient(**self.patient_data)
        expected = f"{patient.first_name} {patient.last_name}"
        self.assertEqual(str(patient), expected)

class FileModelTests(TestCase):
    def setUp(self):
        self.patient = Patient.objects.create(
            first_name='Jane',
            last_name='Smith',
            date_of_birth='1985-05-15',
            email='jane@example.com'
        )

    def test_file_creation_with_uuid(self):
        """Test file creation generates UUID"""
        test_file = SimpleUploadedFile(
            "test.txt", 
            b"file_content", 
            content_type="text/plain"
        )
        
        file_obj = File.objects.create(
            patient=self.patient,
            display_name="Test File",
            file=test_file
        )
        
        self.assertTrue(file_obj.id)
        self.assertEqual(len(str(file_obj.id)), 36)  # UUID length
        self.assertEqual(file_obj.patient, self.patient)

    def test_file_upload_path(self):
        """Test file upload path generation"""
        test_file = SimpleUploadedFile(
            "document.pdf",
            b"pdf_content",
            content_type="application/pdf"
        )
        
        file_obj = File(
            patient=self.patient,
            display_name="Medical Report",
            file=test_file
        )
        
        # Test upload path generation
        upload_path = File.upload_to(file_obj, "document.pdf")
        self.assertIn("uploads/", upload_path)
        self.assertTrue(upload_path.endswith(".pdf"))
```

#### Medical Observation Model Tests
```python
# student_groups/tests.py
from django.test import TestCase
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from patients.models import Patient
from .models import BloodPressure, HeartRate, BodyTemperature, Note

class BloodPressureModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='doctor',
            password='testpass123'
        )
        self.patient = Patient.objects.create(
            first_name='Test',
            last_name='Patient',
            date_of_birth='1990-01-01',
            email='test@example.com'
        )

    def test_blood_pressure_creation(self):
        """Test blood pressure record creation"""
        bp = BloodPressure.objects.create(
            patient=self.patient,
            user=self.user,
            systolic=120,
            diastolic=80
        )
        
        self.assertEqual(bp.systolic, 120)
        self.assertEqual(bp.diastolic, 80)
        self.assertEqual(bp.patient, self.patient)
        self.assertEqual(bp.user, self.user)
        self.assertTrue(bp.created_at)

    def test_blood_pressure_str_representation(self):
        """Test string representation"""
        bp = BloodPressure(
            patient=self.patient,
            user=self.user,
            systolic=120,
            diastolic=80
        )
        expected = f"{self.patient} - 120/80 mmHg ({self.user.username})"
        self.assertEqual(str(bp), expected)

    def test_invalid_blood_pressure_values(self):
        """Test validation of blood pressure values"""
        # Test with validators (if implemented)
        bp = BloodPressure(
            patient=self.patient,
            user=self.user,
            systolic=300,  # Invalid high value
            diastolic=150  # Invalid high value
        )
        
        # This would raise ValidationError if validators are implemented
        # with self.assertRaises(ValidationError):
        #     bp.full_clean()

class ObservationManagerTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='nurse',
            password='testpass123'
        )
        self.patient = Patient.objects.create(
            first_name='Patient',
            last_name='Test',
            date_of_birth='1985-03-20',
            email='patient@example.com'
        )

    def test_bulk_observation_creation(self):
        """Test creating multiple observations at once"""
        from .models import ObservationManager
        
        observation_data = {
            'blood_pressure': {
                'patient': self.patient,
                'user': self.user,
                'systolic': 118,
                'diastolic': 76
            },
            'heart_rate': {
                'patient': self.patient,
                'user': self.user,
                'heart_rate': 72
            },
            'body_temperature': {
                'patient': self.patient,
                'user': self.user,
                'temperature': 36.6
            }
        }
        
        created_observations = ObservationManager.create_observations(observation_data)
        
        self.assertIn('blood_pressure', created_observations)
        self.assertIn('heart_rate', created_observations)
        self.assertIn('body_temperature', created_observations)
        
        # Verify objects were created
        self.assertEqual(BloodPressure.objects.count(), 1)
        self.assertEqual(HeartRate.objects.count(), 1)
        self.assertEqual(BodyTemperature.objects.count(), 1)
```

### Serializer Testing

```python
# patients/tests.py
from rest_framework.test import APITestCase
from rest_framework import serializers
from .serializers import PatientSerializer

class PatientSerializerTests(APITestCase):
    def setUp(self):
        self.valid_data = {
            'first_name': 'Alice',
            'last_name': 'Johnson',
            'date_of_birth': '1992-07-10',
            'email': 'alice@example.com',
            'phone_number': '+1555987654'
        }

    def test_valid_serializer_data(self):
        """Test serializer with valid data"""
        serializer = PatientSerializer(data=self.valid_data)
        self.assertTrue(serializer.is_valid())
        
        patient = serializer.save()
        self.assertEqual(patient.first_name, 'Alice')
        self.assertEqual(patient.email, 'alice@example.com')

    def test_missing_required_fields(self):
        """Test serializer validation with missing fields"""
        incomplete_data = {'first_name': 'John'}
        serializer = PatientSerializer(data=incomplete_data)
        
        self.assertFalse(serializer.is_valid())
        self.assertIn('last_name', serializer.errors)
        self.assertIn('date_of_birth', serializer.errors)
        self.assertIn('email', serializer.errors)

    def test_invalid_email_format(self):
        """Test email validation"""
        invalid_data = self.valid_data.copy()
        invalid_data['email'] = 'invalid-email-format'
        
        serializer = PatientSerializer(data=invalid_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('email', serializer.errors)

    def test_serializer_output(self):
        """Test serializer output includes all expected fields"""
        patient = Patient.objects.create(**self.valid_data)
        serializer = PatientSerializer(patient)
        
        self.assertIn('id', serializer.data)
        self.assertIn('first_name', serializer.data)
        self.assertIn('created_at', serializer.data)
        self.assertIn('updated_at', serializer.data)
```

## API Testing

### Authentication Testing

```python
# Base test class for authenticated requests
from rest_framework.test import APITestCase
from rest_framework import status
from django.contrib.auth.models import User

class AuthenticatedAPITestCase(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user)

class UnauthenticatedAPITestCase(APITestCase):
    def test_unauthenticated_access_denied(self):
        """Test that unauthenticated requests are denied"""
        response = self.client.get('/api/patients/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
```

### Patient API Testing

```python
class PatientAPITests(AuthenticatedAPITestCase):
    def setUp(self):
        super().setUp()
        self.patient_data = {
            'first_name': 'Emma',
            'last_name': 'Wilson',
            'date_of_birth': '1988-11-22',
            'email': 'emma@example.com',
            'phone_number': '+1555234567'
        }

    def test_create_patient(self):
        """Test patient creation via API"""
        response = self.client.post('/api/patients/', self.patient_data)
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Patient.objects.count(), 1)
        
        patient = Patient.objects.get()
        self.assertEqual(patient.first_name, 'Emma')
        self.assertEqual(patient.email, 'emma@example.com')

    def test_list_patients(self):
        """Test patient listing"""
        # Create test patients
        Patient.objects.create(
            first_name='John',
            last_name='Doe',
            date_of_birth='1990-01-01',
            email='john@example.com'
        )
        Patient.objects.create(
            first_name='Jane',
            last_name='Smith',
            date_of_birth='1985-05-15',
            email='jane@example.com'
        )
        
        response = self.client.get('/api/patients/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(len(response.data['results']), 2)

    def test_get_patient_detail(self):
        """Test retrieving patient details"""
        patient = Patient.objects.create(**self.patient_data)
        
        response = self.client.get(f'/api/patients/{patient.id}/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], patient.id)
        self.assertEqual(response.data['first_name'], 'Emma')

    def test_update_patient(self):
        """Test patient update"""
        patient = Patient.objects.create(**self.patient_data)
        
        update_data = {'phone_number': '+1555999888'}
        response = self.client.patch(f'/api/patients/{patient.id}/', update_data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        patient.refresh_from_db()
        self.assertEqual(patient.phone_number, '+1555999888')

    def test_delete_patient(self):
        """Test patient deletion"""
        patient = Patient.objects.create(**self.patient_data)
        
        response = self.client.delete(f'/api/patients/{patient.id}/')
        
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Patient.objects.count(), 0)

    def test_patient_search(self):
        """Test patient search functionality"""
        Patient.objects.create(
            first_name='John',
            last_name='Doe',
            date_of_birth='1990-01-01',
            email='john@example.com'
        )
        Patient.objects.create(
            first_name='Jane',
            last_name='Doe',
            date_of_birth='1985-05-15',
            email='jane@example.com'
        )
        
        # Search by name
        response = self.client.get('/api/patients/?search=John')
        self.assertEqual(response.data['count'], 1)
        
        # Search by last name
        response = self.client.get('/api/patients/?search=Doe')
        self.assertEqual(response.data['count'], 2)

    def test_patient_filtering(self):
        """Test patient filtering"""
        Patient.objects.create(
            first_name='John',
            last_name='Doe',
            date_of_birth='1990-01-01',
            email='john@example.com'
        )
        Patient.objects.create(
            first_name='John',
            last_name='Smith',
            date_of_birth='1985-05-15',
            email='johnsmith@example.com'
        )
        
        response = self.client.get('/api/patients/?first_name=John')
        self.assertEqual(response.data['count'], 2)
        
        response = self.client.get('/api/patients/?last_name=Doe')
        self.assertEqual(response.data['count'], 1)

    def test_patient_ordering(self):
        """Test patient ordering"""
        patient1 = Patient.objects.create(
            first_name='Alice',
            last_name='Smith',
            date_of_birth='1990-01-01',
            email='alice@example.com'
        )
        patient2 = Patient.objects.create(
            first_name='Bob',
            last_name='Jones',
            date_of_birth='1985-05-15',
            email='bob@example.com'
        )
        
        # Order by last name
        response = self.client.get('/api/patients/?ordering=last_name')
        results = response.data['results']
        self.assertEqual(results[0]['id'], patient2.id)  # Jones comes before Smith
        
        # Reverse order
        response = self.client.get('/api/patients/?ordering=-last_name')
        results = response.data['results']
        self.assertEqual(results[0]['id'], patient1.id)  # Smith comes before Jones
```

### File Upload API Testing

```python
class FileAPITests(AuthenticatedAPITestCase):
    def setUp(self):
        super().setUp()
        self.patient = Patient.objects.create(
            first_name='Test',
            last_name='Patient',
            date_of_birth='1990-01-01',
            email='test@example.com'
        )

    def test_file_upload(self):
        """Test file upload for patient"""
        test_file = SimpleUploadedFile(
            "test_document.pdf",
            b"fake pdf content",
            content_type="application/pdf"
        )
        
        data = {
            'file': test_file,
            'display_name': 'Medical Report'
        }
        
        response = self.client.post(
            f'/api/patients/{self.patient.id}/files/',
            data,
            format='multipart'
        )
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(File.objects.count(), 1)
        
        file_obj = File.objects.get()
        self.assertEqual(file_obj.display_name, 'Medical Report')
        self.assertEqual(file_obj.patient, self.patient)

    def test_list_patient_files(self):
        """Test listing files for a patient"""
        # Create test files
        File.objects.create(
            patient=self.patient,
            display_name="File 1",
            file=SimpleUploadedFile("file1.txt", b"content1")
        )
        File.objects.create(
            patient=self.patient,
            display_name="File 2",
            file=SimpleUploadedFile("file2.txt", b"content2")
        )
        
        response = self.client.get(f'/api/patients/{self.patient.id}/files/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 2)

    def test_delete_patient_file(self):
        """Test deleting a patient file"""
        file_obj = File.objects.create(
            patient=self.patient,
            display_name="Test File",
            file=SimpleUploadedFile("test.txt", b"content")
        )
        
        response = self.client.delete(
            f'/api/patients/{self.patient.id}/files/{file_obj.id}/'
        )
        
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(File.objects.count(), 0)

    def test_file_access_restricted_to_patient(self):
        """Test that files are only accessible for their patient"""
        other_patient = Patient.objects.create(
            first_name='Other',
            last_name='Patient',
            date_of_birth='1985-01-01',
            email='other@example.com'
        )
        
        file_obj = File.objects.create(
            patient=other_patient,
            display_name="Private File",
            file=SimpleUploadedFile("private.txt", b"private content")
        )
        
        # Try to access file through wrong patient
        response = self.client.get(
            f'/api/patients/{self.patient.id}/files/{file_obj.id}/'
        )
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
```

### Medical Observations API Testing

```python
class ObservationAPITests(AuthenticatedAPITestCase):
    def setUp(self):
        super().setUp()
        self.patient = Patient.objects.create(
            first_name='Patient',
            last_name='Test',
            date_of_birth='1990-01-01',
            email='patient@example.com'
        )

    def test_create_blood_pressure(self):
        """Test blood pressure creation"""
        data = {
            'patient': self.patient.id,
            'systolic': 120,
            'diastolic': 80
        }
        
        response = self.client.post(
            '/api/student-groups/observations/blood-pressures/',
            data
        )
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(BloodPressure.objects.count(), 1)
        
        bp = BloodPressure.objects.get()
        self.assertEqual(bp.systolic, 120)
        self.assertEqual(bp.user, self.user)

    def test_create_heart_rate(self):
        """Test heart rate creation"""
        data = {
            'patient': self.patient.id,
            'heart_rate': 72
        }
        
        response = self.client.post(
            '/api/student-groups/observations/heart-rates/',
            data
        )
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(HeartRate.objects.count(), 1)

    def test_create_body_temperature(self):
        """Test body temperature creation"""
        data = {
            'patient': self.patient.id,
            'temperature': '36.5'
        }
        
        response = self.client.post(
            '/api/student-groups/observations/body-temperatures/',
            data
        )
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(BodyTemperature.objects.count(), 1)

    def test_bulk_observation_creation(self):
        """Test creating multiple observations at once"""
        data = {
            'patient': self.patient.id,
            'blood_pressure': {
                'systolic': 118,
                'diastolic': 76
            },
            'heart_rate': {
                'heart_rate': 68
            },
            'body_temperature': {
                'temperature': '36.8'
            }
        }
        
        response = self.client.post(
            '/api/student-groups/observations/',
            data,
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(BloodPressure.objects.count(), 1)
        self.assertEqual(HeartRate.objects.count(), 1)
        self.assertEqual(BodyTemperature.objects.count(), 1)

    def test_list_observations_by_patient(self):
        """Test filtering observations by patient"""
        # Create observations for this patient
        BloodPressure.objects.create(
            patient=self.patient,
            user=self.user,
            systolic=120,
            diastolic=80
        )
        
        # Create observation for different patient
        other_patient = Patient.objects.create(
            first_name='Other',
            last_name='Patient',
            date_of_birth='1985-01-01',
            email='other@example.com'
        )
        BloodPressure.objects.create(
            patient=other_patient,
            user=self.user,
            systolic=130,
            diastolic=85
        )
        
        response = self.client.get(
            f'/api/student-groups/observations/blood-pressures/?patient={self.patient.id}'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
```

## Integration Testing

### Complete Workflow Tests

```python
class PatientWorkflowIntegrationTests(AuthenticatedAPITestCase):
    def test_complete_patient_management_workflow(self):
        """Test complete patient lifecycle"""
        
        # 1. Create patient
        patient_data = {
            'first_name': 'Integration',
            'last_name': 'Test',
            'date_of_birth': '1990-01-01',
            'email': 'integration@example.com'
        }
        
        response = self.client.post('/api/patients/', patient_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        patient_id = response.data['id']
        
        # 2. Upload patient file
        test_file = SimpleUploadedFile(
            "medical_report.pdf",
            b"fake pdf content",
            content_type="application/pdf"
        )
        
        file_data = {
            'file': test_file,
            'display_name': 'Initial Medical Report'
        }
        
        response = self.client.post(
            f'/api/patients/{patient_id}/files/',
            file_data,
            format='multipart'
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # 3. Record medical observations
        bp_data = {
            'patient': patient_id,
            'systolic': 125,
            'diastolic': 82
        }
        response = self.client.post(
            '/api/student-groups/observations/blood-pressures/',
            bp_data
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # 4. Add patient note
        note_data = {
            'patient': patient_id,
            'content': 'Patient shows good progress in recovery.'
        }
        response = self.client.post(
            '/api/student-groups/notes/',
            note_data
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # 5. Verify all data is associated correctly
        patient = Patient.objects.get(id=patient_id)
        self.assertEqual(patient.files.count(), 1)
        self.assertEqual(patient.blood_pressures.count(), 1)
        self.assertEqual(patient.notes.count(), 1)
        
        # 6. Update patient information
        update_data = {'phone_number': '+1555123456'}
        response = self.client.patch(f'/api/patients/{patient_id}/', update_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # 7. Verify relationships are maintained after update
        patient.refresh_from_db()
        self.assertEqual(patient.phone_number, '+1555123456')
        self.assertEqual(patient.files.count(), 1)
        self.assertEqual(patient.blood_pressures.count(), 1)

    def test_patient_deletion_cascades(self):
        """Test that patient deletion removes associated data"""
        # Create patient with associated data
        patient = Patient.objects.create(
            first_name='Delete',
            last_name='Test',
            date_of_birth='1990-01-01',
            email='delete@example.com'
        )
        
        # Add file
        File.objects.create(
            patient=patient,
            display_name="File to delete",
            file=SimpleUploadedFile("delete.txt", b"content")
        )
        
        # Add observations
        BloodPressure.objects.create(
            patient=patient,
            user=self.user,
            systolic=120,
            diastolic=80
        )
        
        Note.objects.create(
            patient=patient,
            user=self.user,
            content="Note to delete"
        )
        
        # Verify data exists
        self.assertEqual(File.objects.filter(patient=patient).count(), 1)
        self.assertEqual(BloodPressure.objects.filter(patient=patient).count(), 1)
        self.assertEqual(Note.objects.filter(patient=patient).count(), 1)
        
        # Delete patient
        response = self.client.delete(f'/api/patients/{patient.id}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        
        # Verify cascade deletion
        self.assertEqual(Patient.objects.filter(id=patient.id).count(), 0)
        self.assertEqual(File.objects.filter(patient_id=patient.id).count(), 0)
        self.assertEqual(BloodPressure.objects.filter(patient_id=patient.id).count(), 0)
        self.assertEqual(Note.objects.filter(patient_id=patient.id).count(), 0)
```

## Test Data Management

### Using Factories

```bash
# Install factory-boy
uv add --dev factory-boy
```

```python
# tests/factories.py
import factory
from django.contrib.auth.models import User
from patients.models import Patient, File
from student_groups.models import BloodPressure, HeartRate, Note

class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User
    
    username = factory.Sequence(lambda n: f"user{n}")
    email = factory.LazyAttribute(lambda obj: f"{obj.username}@example.com")
    first_name = factory.Faker('first_name')
    last_name = factory.Faker('last_name')

class PatientFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Patient
    
    first_name = factory.Faker('first_name')
    last_name = factory.Faker('last_name')
    date_of_birth = factory.Faker('date_of_birth', minimum_age=18, maximum_age=90)
    email = factory.LazyAttribute(
        lambda obj: f"{obj.first_name.lower()}.{obj.last_name.lower()}@example.com"
    )
    phone_number = factory.Faker('phone_number')

class FileFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = File
    
    patient = factory.SubFactory(PatientFactory)
    display_name = factory.Faker('sentence', nb_words=3)
    file = factory.django.FileField(filename='test.pdf')

class BloodPressureFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = BloodPressure
    
    patient = factory.SubFactory(PatientFactory)
    user = factory.SubFactory(UserFactory)
    systolic = factory.Faker('random_int', min=90, max=180)
    diastolic = factory.Faker('random_int', min=60, max=120)

class NoteFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Note
    
    patient = factory.SubFactory(PatientFactory)
    user = factory.SubFactory(UserFactory)
    content = factory.Faker('text', max_nb_chars=500)
```

### Using Factories in Tests

```python
from tests.factories import PatientFactory, BloodPressureFactory, UserFactory

class PatientFactoryTests(AuthenticatedAPITestCase):
    def test_create_patients_with_factory(self):
        """Test creating patients using factory"""
        patients = PatientFactory.create_batch(5)
        
        self.assertEqual(Patient.objects.count(), 5)
        
        for patient in patients:
            self.assertTrue(patient.first_name)
            self.assertTrue(patient.email)
            self.assertIn('@example.com', patient.email)

    def test_create_patient_with_observations(self):
        """Test creating patient with related observations"""
        patient = PatientFactory()
        user = UserFactory()
        
        # Create multiple blood pressure readings
        BloodPressureFactory.create_batch(3, patient=patient, user=user)
        
        self.assertEqual(patient.blood_pressures.count(), 3)
        
        # Test API response includes related data
        response = self.client.get(f'/api/patients/{patient.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
```

### Fixtures

```python
# Create fixtures
uv run python manage.py dumpdata patients.Patient > patients/fixtures/test_patients.json
uv run python manage.py dumpdata auth.User > fixtures/test_users.json

# Use in tests
class PatientFixtureTests(TestCase):
    fixtures = ['test_users.json', 'test_patients.json']
    
    def test_with_fixture_data(self):
        self.assertTrue(Patient.objects.exists())
        self.assertTrue(User.objects.exists())
```

## Coverage Analysis

### Installing Coverage Tools

```bash
# Add coverage tools
uv add --dev coverage django-coverage-plugin
```

### Running Coverage Analysis

```bash
# Run tests with coverage
uv run coverage run --source='.' manage.py test

# Generate coverage report
uv run coverage report

# Generate HTML coverage report
uv run coverage html

# Open HTML report
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

### Coverage Configuration

```ini
# .coveragerc
[run]
source = .
omit = 
    */migrations/*
    */venv/*
    */env/*
    manage.py
    */settings/*
    */tests/*
    */test_*
    */conftest.py

[report]
exclude_lines =
    pragma: no cover
    def __repr__
    if self.debug:
    if settings.DEBUG
    raise AssertionError
    raise NotImplementedError
    if 0:
    if __name__ == .__main__.:

[html]
directory = htmlcov
```

### Coverage Goals

- **Overall Coverage**: > 90%
- **Models**: > 95%
- **Views**: > 90%
- **Serializers**: > 95%
- **Business Logic**: 100%

## Performance Testing

### Load Testing with Django

```python
# tests/test_performance.py
from django.test import TestCase, TransactionTestCase
from django.test.utils import override_settings
from django.db import transaction
import time

class PerformanceTests(TransactionTestCase):
    def test_patient_creation_performance(self):
        """Test patient creation performance"""
        start_time = time.time()
        
        # Create 100 patients
        for i in range(100):
            Patient.objects.create(
                first_name=f'Patient{i}',
                last_name='Test',
                date_of_birth='1990-01-01',
                email=f'patient{i}@example.com'
            )
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Should complete in under 5 seconds
        self.assertLess(duration, 5.0)
        print(f"Created 100 patients in {duration:.2f} seconds")

    def test_bulk_observation_creation(self):
        """Test bulk observation creation performance"""
        patient = Patient.objects.create(
            first_name='Test',
            last_name='Patient',
            date_of_birth='1990-01-01',
            email='test@example.com'
        )
        
        start_time = time.time()
        
        # Create observations in bulk
        observations = []
        for i in range(1000):
            observations.append(BloodPressure(
                patient=patient,
                user_id=1,  # Assuming user exists
                systolic=120 + (i % 20),
                diastolic=80 + (i % 15)
            ))
        
        BloodPressure.objects.bulk_create(observations)
        
        end_time = time.time()
        duration = end_time - start_time
        
        self.assertLess(duration, 2.0)
        print(f"Created 1000 observations in {duration:.2f} seconds")

    @override_settings(DEBUG=False)
    def test_api_response_time(self):
        """Test API response times"""
        # Create test data
        PatientFactory.create_batch(50)
        
        start_time = time.time()
        response = self.client.get('/api/patients/')
        end_time = time.time()
        
        duration = end_time - start_time
        
        self.assertEqual(response.status_code, 200)
        self.assertLess(duration, 1.0)  # Should respond in under 1 second
        print(f"API response time: {duration:.3f} seconds")
```

### Database Query Performance

```python
from django.test import TestCase
from django.test.utils import override_settings
from django.db import connection
from django.test import TestCase

class QueryPerformanceTests(TestCase):
    def test_patient_list_query_count(self):
        """Test that patient list doesn't have N+1 query problem"""
        PatientFactory.create_batch(10)
        
        with self.assertNumQueries(1):  # Should only make 1 query
            list(Patient.objects.all())

    def test_patient_with_files_query_count(self):
        """Test optimized queries with related objects"""
        patients = PatientFactory.create_batch(5)
        for patient in patients:
            FileFactory.create_batch(3, patient=patient)
        
        # Without optimization - would be N+1 queries
        with self.assertNumQueries(6):  # 1 for patients + 5 for files
            for patient in Patient.objects.all():
                list(patient.files.all())
        
        # With optimization - should be 2 queries
        with self.assertNumQueries(2):  # 1 for patients + 1 for files
            for patient in Patient.objects.prefetch_related('files'):
                list(patient.files.all())
```

## Manual Testing

### Test Scenarios

#### Patient Management
1. **Create Patient**
   - Navigate to `/admin/patients/patient/add/`
   - Fill in all required fields
   - Verify patient is created successfully
   - Check email uniqueness validation

2. **Upload Files**
   - Use API endpoint or admin interface
   - Upload various file types (PDF, DOCX, images)
   - Verify file size limits
   - Check file download functionality

3. **Record Observations**
   - Add blood pressure readings
   - Record heart rate measurements
   - Enter body temperature
   - Verify validation rules

#### API Testing
1. **Authentication**
   - Test login/logout flow
   - Verify unauthorized access is blocked
   - Test session management

2. **CRUD Operations**
   - Create, read, update, delete patients
   - Test file upload and deletion
   - Verify observation recording

3. **Error Handling**
   - Test with invalid data
   - Verify error messages are helpful
   - Check HTTP status codes

### Manual Test Checklist

```markdown
## Patient Management
- [ ] Create patient with valid data
- [ ] Create patient with invalid email
- [ ] Create patient with duplicate email
- [ ] Update patient information
- [ ] Delete patient
- [ ] Search patients by name
- [ ] Filter patients by criteria

## File Management
- [ ] Upload PDF file
- [ ] Upload image file
- [ ] Upload large file (test size limit)
- [ ] Upload invalid file type
- [ ] Download file
- [ ] Delete file
- [ ] View file list

## Medical Observations
- [ ] Record blood pressure
- [ ] Record heart rate
- [ ] Record body temperature
- [ ] Create bulk observations
- [ ] View observation history
- [ ] Validate observation values

## API Functionality
- [ ] Authentication required
- [ ] Pagination works correctly
- [ ] Search and filtering
- [ ] Error responses are helpful
- [ ] API documentation accessible
```

## Continuous Integration

### GitHub Actions Configuration

```yaml
# .github/workflows/django.yml
name: Django CI

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: [3.12]

    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}
    
    - name: Install uv
      run: curl -LsSf https://astral.sh/uv/install.sh | sh
    
    - name: Install dependencies
      run: |
        export PATH="$HOME/.cargo/bin:$PATH"
        uv sync
    
    - name: Run migrations
      run: |
        export PATH="$HOME/.cargo/bin:$PATH"
        uv run python manage.py migrate
    
    - name: Run tests with coverage
      run: |
        export PATH="$HOME/.cargo/bin:$PATH"
        uv run coverage run --source='.' manage.py test
        uv run coverage xml
    
    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
        flags: unittests
        name: codecov-umbrella
        fail_ci_if_error: true
```

### Pre-commit Hooks

```bash
# Install pre-commit
uv add --dev pre-commit

# Create .pre-commit-config.yaml
```

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/psf/black
    rev: 23.3.0
    hooks:
      - id: black
        language_version: python3

  - repo: https://github.com/pycqa/isort
    rev: 5.12.0
    hooks:
      - id: isort

  - repo: https://github.com/pycqa/flake8
    rev: 6.0.0
    hooks:
      - id: flake8

  - repo: local
    hooks:
      - id: django-tests
        name: django-tests
        entry: uv run python manage.py test
        language: system
        pass_filenames: false
        always_run: true
```

```bash
# Install pre-commit hooks
uv run pre-commit install
```

---

## Quick Testing Reference

### Run Tests
```bash
# All tests
./start.sh test

# Specific app
uv run python manage.py test patients

# With coverage
uv run coverage run --source='.' manage.py test
uv run coverage report
```

### Test Categories
- **Unit Tests**: Test individual components
- **API Tests**: Test REST endpoints
- **Integration Tests**: Test complete workflows
- **Performance Tests**: Test response times and load

### Best Practices
- Write tests before implementation (TDD)
- Use factories for test data
- Test both success and failure cases
- Keep tests isolated and independent
- Aim for high code coverage
- Use descriptive test names
