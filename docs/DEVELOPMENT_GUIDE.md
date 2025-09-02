# DMR Project Development Guide

## Table of Contents
1. [Project Overview](#project-overview)
2. [Prerequisites](#prerequisites)
3. [Quick Start](#quick-start)
4. [Project Architecture](#project-architecture)
5. [Development Environment Setup](#development-environment-setup)
6. [Database Setup and Management](#database-setup-and-management)
7. [API Development](#api-development)
8. [Testing](#testing)
9. [Code Style and Standards](#code-style-and-standards)
10. [Deployment](#deployment)
11. [Troubleshooting](#troubleshooting)

## Project Overview

The Digital Medical Records (DMR) system is a Django REST API backend designed for medical record simulation and management. The system provides:

- **Patient Management**: Complete patient information and file management
- **Medical Observations**: Recording of vital signs (blood pressure, heart rate, body temperature)
- **Student Groups**: Medical student grouping and management functionality
- **REST API**: Full RESTful API with automatic documentation
- **Admin Interface**: Django admin panel for system management

### Key Features
- ✅ Patient information and file upload management
- ✅ Vital signs tracking and validation
- ✅ Student group management with role-based access
- ✅ Comprehensive REST API with Swagger documentation
- ✅ Authentication and authorization
- ✅ File upload and media management

## Prerequisites

Before starting development, ensure you have the following installed:

### Required Software
- **Python 3.12+**: The project requires Python 3.12 or higher
- **uv**: Modern Python package installer and resolver
- **Git**: For version control
- **SQLite**: Default database (included with Python)

### Optional but Recommended
- **VS Code** or **PyCharm**: IDE with Python support
- **Postman** or **Insomnia**: API testing tools
- **Docker**: For containerized deployment (future)

### Installing Prerequisites

#### 1. Install Python 3.12+
```bash
# macOS (using Homebrew)
brew install python@3.12

# Ubuntu/Debian
sudo apt update
sudo apt install python3.12 python3.12-venv python3.12-pip

# Windows
# Download from https://www.python.org/downloads/
```

#### 2. Install uv Package Manager
```bash
# Unix/macOS
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# Or via pip
pip install uv
```

## Quick Start

### 1. Clone and Setup
```bash
# Clone the repository
git clone https://github.com/UWA-CITS5206-DMR/dmrserver
cd dmrserver

# Initialize the project (first time setup)
./start.sh init
```

### 2. Start Development
```bash
# Start development server (foreground)
./start.sh dev

# Or start in background
./start.sh dev-bg

# Check status
./start.sh status
```

### 3. Access the Application
- **API Documentation**: http://127.0.0.1:8000/schema/swagger-ui/
- **Admin Panel**: http://127.0.0.1:8000/admin/
- **API Root**: http://127.0.0.1:8000/api/

## Project Architecture

### Directory Structure
```
dmrserver/
├── dmr/                    # Django project configuration
│   ├── settings.py         # Project settings
│   ├── urls.py            # Main URL configuration
│   ├── wsgi.py            # WSGI application
│   └── asgi.py            # ASGI application
├── patients/              # Patient management app
│   ├── models.py          # Patient and File models
│   ├── serializers.py     # DRF serializers
│   ├── views.py           # API views
│   ├── urls.py            # App URLs
│   ├── admin.py           # Admin configuration
│   └── tests.py           # Unit tests
├── student_groups/        # Student group management app
│   ├── models.py          # Medical observation models
│   ├── serializers.py     # DRF serializers
│   ├── views.py           # API views
│   ├── urls.py            # App URLs
│   ├── validators.py      # Custom validators
│   └── tests.py           # Unit tests
├── docs/                  # Documentation
├── media/                 # User uploaded files
├── static/                # Static files
├── manage.py              # Django management script
├── start.sh               # Project startup script
├── pyproject.toml         # Project dependencies
└── README.md              # Basic project info
```

### Architecture Components

#### 1. Django Apps
- **patients**: Handles patient information and file management
- **student_groups**: Manages medical observations and student groupings

#### 2. Models Overview
```python
# patients/models.py
- Patient: Core patient information
- File: Patient file uploads with UUID naming

# student_groups/models.py
- Note: Patient notes and observations
- BloodPressure: Blood pressure readings
- HeartRate: Heart rate measurements
- BodyTemperature: Body temperature records
- ObservationManager: Business logic for observations
```

#### 3. API Structure
```
/api/
├── patients/              # Patient CRUD operations
│   └── {id}/files/        # Nested file operations
├── student-groups/        # Student group operations
│   ├── notes/             # Patient notes
│   └── observations/      # Medical observations
│       ├── blood-pressures/
│       ├── heart-rates/
│       └── body-temperatures/
├── schema/                # OpenAPI schema
└── docs/                  # Swagger UI
```

## Development Environment Setup

### 1. Detailed Initial Setup

#### Clone and Enter Project
```bash
git clone https://github.com/UWA-CITS5206-DMR/dmrserver
cd dmrserver
```

#### Verify Python Version
```bash
python3 --version  # Should be 3.12+
```

#### Install and Setup Dependencies
```bash
# Install uv if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Sync dependencies and create virtual environment
uv sync

# Verify installation
uv run python --version
```

### 2. Environment Configuration

#### Create .env file (optional)
```bash
# Create environment file
touch .env

# Add the following content to .env:
DEBUG=True
SECRET_KEY=your-secret-key-here
ALLOWED_HOSTS=localhost,127.0.0.1
DATABASE_URL=sqlite:///db.sqlite3
```

#### Configure Django Settings
The project uses SQLite by default, which requires no additional configuration for development.

### 3. IDE Setup

#### VS Code Setup
1. Install Python extension
2. Open project folder
3. Select Python interpreter: `Ctrl+Shift+P` → "Python: Select Interpreter" → Choose the uv virtual environment

#### PyCharm Setup
1. Open project folder
2. Configure Python interpreter: Settings → Project → Python Interpreter
3. Add interpreter from the `.venv` folder created by uv

## Database Setup and Management

### 1. Initial Database Setup
```bash
# Create and apply initial migrations
./start.sh migrate

# Create a superuser account
./start.sh create-superuser
```

### 2. Working with Migrations

#### Creating New Migrations
```bash
# When you modify models, create migrations
uv run python manage.py makemigrations

# Apply migrations
uv run python manage.py migrate

# Or use the script
./start.sh migrate
```

#### Migration Best Practices
1. **Always create migrations for model changes**
2. **Review migration files before applying**
3. **Use descriptive migration names when needed**
```bash
uv run python manage.py makemigrations --name add_patient_phone_field patients
```

### 3. Database Management Commands

#### Reset Database (Development Only)
```bash
# Stop the server first
./start.sh stop

# Remove database
rm db.sqlite3

# Recreate and migrate
./start.sh migrate
./start.sh create-superuser
```

#### Backup and Restore
```bash
# Backup database
cp db.sqlite3 db_backup_$(date +%Y%m%d_%H%M%S).sqlite3

# Create fixtures (data backup)
uv run python manage.py dumpdata > fixtures/initial_data.json

# Load fixtures
./start.sh load-fixtures
```

## API Development

### 1. Understanding the API Structure

#### Authentication
The API uses Django's session authentication by default:
```python
# In settings.py
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
}
```

#### API Endpoints Overview
```bash
# List all available endpoints
uv run python manage.py show_urls

# Or check the API root
curl http://127.0.0.1:8000/api/
```

### 2. Adding New Models

#### Step 1: Define the Model
```python
# Example: patients/models.py
class MedicalHistory(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    condition = models.CharField(max_length=200)
    diagnosed_date = models.DateField()
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Medical History"
        verbose_name_plural = "Medical Histories"
        ordering = ['-diagnosed_date']

    def __str__(self):
        return f"{self.patient} - {self.condition}"
```

#### Step 2: Create and Apply Migration
```bash
uv run python manage.py makemigrations patients
uv run python manage.py migrate
```

#### Step 3: Create Serializer
```python
# patients/serializers.py
class MedicalHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = MedicalHistory
        fields = '__all__'
        read_only_fields = ('created_at',)

    def validate_diagnosed_date(self, value):
        if value > timezone.now().date():
            raise serializers.ValidationError(
                "Diagnosed date cannot be in the future."
            )
        return value
```

#### Step 4: Create ViewSet
```python
# patients/views.py
class MedicalHistoryViewSet(viewsets.ModelViewSet):
    serializer_class = MedicalHistorySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return MedicalHistory.objects.filter(
            patient_id=self.kwargs['patient_pk']
        )

    def perform_create(self, serializer):
        serializer.save(patient_id=self.kwargs['patient_pk'])
```

#### Step 5: Add to URLs
```python
# patients/urls.py
medical_history_router = routers.NestedSimpleRouter(
    router, r'patients', lookup='patient'
)
medical_history_router.register(
    r'medical-history', MedicalHistoryViewSet, basename='medical-history'
)

urlpatterns = router.urls + files_router.urls + medical_history_router.urls
```

### 3. API Testing

#### Using Django Shell
```bash
./start.sh shell

# In the shell:
from patients.models import Patient
from django.contrib.auth.models import User

# Create test data
user = User.objects.create_user('testuser', 'test@example.com', 'password')
patient = Patient.objects.create(
    first_name='John',
    last_name='Doe',
    date_of_birth='1990-01-01',
    email='john@example.com'
)
```

#### Using curl
```bash
# Login first (get session cookie)
curl -X POST http://127.0.0.1:8000/api-auth/login/ \
     -d "username=admin&password=your_password"

# Test API endpoints
curl -b cookies.txt http://127.0.0.1:8000/api/patients/

# With authentication header (if using token auth)
curl -H "Authorization: Token your_token_here" \
     http://127.0.0.1:8000/api/patients/
```

#### Using Python requests
```python
import requests

# Login and get session
session = requests.Session()
login_data = {'username': 'admin', 'password': 'your_password'}
session.post('http://127.0.0.1:8000/api-auth/login/', data=login_data)

# Make API calls
response = session.get('http://127.0.0.1:8000/api/patients/')
print(response.json())
```

## Testing

### 1. Running Tests

#### Run All Tests
```bash
# Using the script
./start.sh test

# Or directly
uv run python manage.py test

# Run specific app tests
uv run python manage.py test patients
uv run python manage.py test student_groups
```

#### Run Tests with Coverage
```bash
# Install coverage
uv add coverage

# Run with coverage
uv run coverage run --source='.' manage.py test
uv run coverage report
uv run coverage html  # Generate HTML report
```

### 2. Writing Tests

#### Model Tests Example
```python
# patients/tests.py
from django.test import TestCase
from django.core.exceptions import ValidationError
from .models import Patient

class PatientModelTests(TestCase):
    def setUp(self):
        self.patient_data = {
            'first_name': 'John',
            'last_name': 'Doe',
            'date_of_birth': '1990-01-01',
            'email': 'john@example.com'
        }

    def test_patient_creation(self):
        patient = Patient.objects.create(**self.patient_data)
        self.assertEqual(patient.first_name, 'John')
        self.assertEqual(str(patient), 'John Doe')

    def test_email_uniqueness(self):
        Patient.objects.create(**self.patient_data)
        with self.assertRaises(ValidationError):
            duplicate_patient = Patient(**self.patient_data)
            duplicate_patient.full_clean()
```

#### API Tests Example
```python
# patients/tests.py
from rest_framework.test import APITestCase
from rest_framework import status
from django.contrib.auth.models import User
from .models import Patient

class PatientAPITests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user)

    def test_create_patient(self):
        data = {
            'first_name': 'Jane',
            'last_name': 'Smith',
            'date_of_birth': '1985-05-15',
            'email': 'jane@example.com'
        }
        response = self.client.post('/api/patients/', data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Patient.objects.count(), 1)

    def test_list_patients(self):
        Patient.objects.create(
            first_name='Test',
            last_name='Patient',
            date_of_birth='1990-01-01',
            email='test@example.com'
        )
        response = self.client.get('/api/patients/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
```

### 3. Test Data Management

#### Using Fixtures
```python
# Create fixtures
uv run python manage.py dumpdata patients.Patient > patients/fixtures/test_patients.json

# Load in tests
class PatientAPITests(APITestCase):
    fixtures = ['test_patients.json']
```

#### Using Factory Boy (Recommended)
```bash
# Install factory boy
uv add factory-boy

# Create factories
# patients/factories.py
import factory
from django.contrib.auth.models import User
from .models import Patient

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
    date_of_birth = factory.Faker('date_of_birth')
    email = factory.LazyAttribute(
        lambda obj: f"{obj.first_name.lower()}.{obj.last_name.lower()}@example.com"
    )
```

## Code Style and Standards

### 1. Python Code Standards

#### Follow PEP 8
```bash
# Install development tools
uv add --dev black isort flake8 mypy

# Format code
uv run black .
uv run isort .

# Check code quality
uv run flake8 .
uv run mypy .
```

#### Code Style Configuration

Create `.flake8`:
```ini
[flake8]
max-line-length = 88
extend-ignore = E203, W503
exclude = migrations, __pycache__, .venv
```

Create `pyproject.toml` section:
```toml
[tool.black]
line-length = 88
target-version = ['py312']
include = '\.pyi?$'
extend-exclude = '''
/(
  migrations
)/
'''

[tool.isort]
profile = "black"
skip = ["migrations"]
```

### 2. Django Best Practices

#### Model Guidelines
```python
class Patient(models.Model):
    # Use descriptive field names
    first_name = models.CharField(max_length=100, verbose_name="First Name")
    
    # Always add verbose names for admin
    date_of_birth = models.DateField(verbose_name="Date of Birth")
    
    # Use appropriate field types
    email = models.EmailField(unique=True, verbose_name="Email Address")
    
    # Add timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Patient"
        verbose_name_plural = "Patients"
        ordering = ["last_name", "first_name"]
    
    def __str__(self):
        return f"{self.first_name} {self.last_name}"
    
    def clean(self):
        # Add custom validation
        if self.date_of_birth > timezone.now().date():
            raise ValidationError("Birth date cannot be in the future")
```

#### Serializer Guidelines
```python
class PatientSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    
    class Meta:
        model = Patient
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')
    
    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}"
    
    def validate_email(self, value):
        # Custom validation
        if Patient.objects.filter(email=value).exists():
            raise serializers.ValidationError("Patient with this email already exists.")
        return value
```

#### ViewSet Guidelines
```python
class PatientViewSet(viewsets.ModelViewSet):
    serializer_class = PatientSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['first_name', 'last_name']
    search_fields = ['first_name', 'last_name', 'email']
    ordering_fields = ['created_at', 'last_name']
    ordering = ['-created_at']
    
    def get_queryset(self):
        return Patient.objects.all()
    
    @action(detail=True, methods=['get'])
    def medical_history(self, request, pk=None):
        patient = self.get_object()
        # Custom endpoint logic
        return Response({'patient': patient.id})
```

### 3. Documentation Standards

#### Docstring Format
```python
def calculate_age(birth_date: date) -> int:
    """
    Calculate age based on birth date.
    
    Args:
        birth_date (date): The birth date of the person
    
    Returns:
        int: Age in years
    
    Raises:
        ValueError: If birth_date is in the future
    
    Example:
        >>> calculate_age(date(1990, 1, 1))
        33
    """
    if birth_date > date.today():
        raise ValueError("Birth date cannot be in the future")
    
    today = date.today()
    return today.year - birth_date.year - (
        (today.month, today.day) < (birth_date.month, birth_date.day)
    )
```

## Deployment

### 1. Production Preparation

#### Environment Variables
```bash
# Create .env.production
DEBUG=False
SECRET_KEY=your-production-secret-key
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
DATABASE_URL=postgresql://user:password@localhost/dbname
```

#### Static Files
```bash
# Collect static files
./start.sh collect-static

# Configure static files serving in production
# Add to settings.py:
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATIC_URL = '/static/'
```

#### Security Settings
```python
# settings.py for production
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
```

### 2. Database Migration in Production

```bash
# Always backup before migration
pg_dump dbname > backup_$(date +%Y%m%d_%H%M%S).sql

# Run migrations
uv run python manage.py migrate

# Collect static files
uv run python manage.py collectstatic --noinput
```

### 3. Health Checks

Create health check endpoint:
```python
# Add to dmr/urls.py
from django.http import JsonResponse
from django.db import connections

def health_check(request):
    try:
        # Check database connection
        connections['default'].cursor()
        return JsonResponse({'status': 'healthy'})
    except Exception as e:
        return JsonResponse({'status': 'unhealthy', 'error': str(e)}, status=500)

urlpatterns = [
    path('health/', health_check),
    # ... other patterns
]
```

## Troubleshooting

### 1. Common Issues

#### Python Version Issues
```bash
# Check Python version
python3 --version

# If wrong version, install correct one
brew install python@3.12  # macOS
sudo apt install python3.12  # Ubuntu
```

#### uv Installation Issues
```bash
# Reinstall uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Add to PATH if needed
export PATH="$HOME/.cargo/bin:$PATH"
echo 'export PATH="$HOME/.cargo/bin:$PATH"' >> ~/.bashrc
```

#### Database Issues
```bash
# Reset database
rm db.sqlite3
./start.sh migrate

# Check database integrity
uv run python manage.py check --database default
```

#### Migration Issues
```bash
# Reset migrations (development only)
rm patients/migrations/0*.py
rm student_groups/migrations/0*.py
./start.sh migrate

# Or fake migrations if needed
uv run python manage.py migrate --fake
```

### 2. Performance Issues

#### Database Query Optimization
```python
# Use select_related for foreign keys
patients = Patient.objects.select_related('user').all()

# Use prefetch_related for many-to-many
patients = Patient.objects.prefetch_related('files').all()

# Add database indexes
class Patient(models.Model):
    email = models.EmailField(unique=True, db_index=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['last_name', 'first_name']),
        ]
```

#### Memory Issues
```bash
# Monitor memory usage
ps aux | grep python

# Reduce memory usage in settings
# Add to settings.py:
DEBUG = False  # In production
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': 'django.log',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}
```

### 3. Getting Help

#### Log Analysis
```bash
# View Django logs
./start.sh logs

# Check system logs (macOS)
tail -f /var/log/system.log

# Check system logs (Linux)
journalctl -f
```

#### Debug Mode
```python
# Enable debug mode temporarily
# In settings.py:
DEBUG = True
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django.db.backends': {
            'level': 'DEBUG',
            'handlers': ['console'],
        },
    },
}
```

#### Useful Django Commands
```bash
# Check project configuration
uv run python manage.py check

# Show all URLs
uv run python manage.py show_urls

# Django shell with models loaded
uv run python manage.py shell_plus

# Create admin user
uv run python manage.py createsuperuser

# Reset admin password
uv run python manage.py changepassword admin
```

## Contributing

### 1. Development Workflow

```bash
# Create feature branch
git checkout -b feature/new-feature

# Make changes and test
./start.sh test

# Format code
uv run black .
uv run isort .

# Commit changes
git add .
git commit -m "Add new feature: description"

# Push and create PR
git push origin feature/new-feature
```

### 2. Code Review Guidelines

- Write clear commit messages
- Add tests for new features
- Update documentation
- Follow coding standards
- Check for security issues

---

## Quick Reference

### Essential Commands
```bash
# Project management
./start.sh init          # First time setup
./start.sh dev           # Start development
./start.sh dev-bg        # Start in background
./start.sh stop          # Stop background service
./start.sh status        # Check status

# Development
./start.sh migrate       # Database migrations
./start.sh shell         # Django shell
./start.sh test          # Run tests
./start.sh logs          # View logs

# Maintenance
./start.sh clean         # Clean project files
./start.sh reinstall     # Reinstall dependencies
```

### Important URLs
- **API Documentation**: http://127.0.0.1:8000/schema/swagger-ui/
- **Admin Panel**: http://127.0.0.1:8000/admin/
- **API Root**: http://127.0.0.1:8000/api/
- **Patients API**: http://127.0.0.1:8000/api/patients/
- **Student Groups**: http://127.0.0.1:8000/api/student-groups/

### Project Structure Quick Reference
```
dmrserver/
├── dmr/              # Project settings
├── patients/         # Patient management
├── student_groups/   # Medical observations
├── docs/            # Documentation
├── start.sh         # Startup script
└── pyproject.toml   # Dependencies
```

Happy coding! 🚀
