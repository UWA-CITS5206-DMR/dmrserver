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

### Test Database

The test database is automatically created and destroyed for each test run.

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
