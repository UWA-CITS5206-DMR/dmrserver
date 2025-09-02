# DMR Project Structure & Architecture

## Table of Contents
1. [Project Overview](#project-overview)
2. [Directory Structure](#directory-structure)
3. [Application Architecture](#application-architecture)
4. [Database Design](#database-design)
5. [API Architecture](#api-architecture)
6. [File Organization](#file-organization)
7. [Configuration Management](#configuration-management)
8. [Security Architecture](#security-architecture)

## Project Overview

The Digital Medical Records (DMR) system is built using Django and Django REST Framework. It follows a modular architecture with clear separation of concerns between different functional areas.

### Technology Stack
- **Backend Framework**: Django 5.2+
- **API Framework**: Django REST Framework 3.16+
- **Database**: SQLite (development) / PostgreSQL (production)
- **Package Manager**: uv
- **Documentation**: drf-spectacular (Swagger/OpenAPI)
- **File Handling**: Django FileField with custom upload paths

## Directory Structure

```
dmrserver/                          # Project root
│
├── dmr/                           # Django project configuration
│   ├── __init__.py
│   ├── asgi.py                   # ASGI configuration
│   ├── settings.py               # Django settings
│   ├── urls.py                   # Main URL configuration
│   └── wsgi.py                   # WSGI configuration
│
├── patients/                      # Patient management application
│   ├── __init__.py
│   ├── admin.py                  # Django admin configuration
│   ├── apps.py                   # App configuration
│   ├── models.py                 # Patient and File models
│   ├── serializers.py            # DRF serializers
│   ├── views.py                  # API views and viewsets
│   ├── urls.py                   # App-specific URLs
│   ├── tests.py                  # Unit tests
│   └── migrations/               # Database migrations
│       ├── __init__.py
│       └── 0001_initial.py
│
├── student_groups/                # Medical observations application
│   ├── __init__.py
│   ├── admin.py                  # Django admin configuration
│   ├── apps.py                   # App configuration
│   ├── models.py                 # Observation models
│   ├── serializers.py            # DRF serializers
│   ├── views.py                  # API views and viewsets
│   ├── urls.py                   # App-specific URLs
│   ├── validators.py             # Custom validation logic
│   ├── tests.py                  # Unit tests
│   └── migrations/               # Database migrations
│       ├── __init__.py
│       └── 0001_initial.py
│
├── docs/                          # Project documentation
│   ├── DEVELOPMENT_GUIDE.md       # Development setup and guidelines
│   ├── API_GUIDE.md              # API documentation
│   └── PROJECT_STRUCTURE.md      # This file
│
├── media/                         # User uploaded files
│   └── uploads/                  # Patient files organized by date
│       └── YYYY/MM/DD/           # Date-based directory structure
│
├── static/                        # Static files (CSS, JS, images)
│   └── admin/                    # Django admin static files
│
├── manage.py                      # Django management script
├── start.sh                       # Project startup script
├── pyproject.toml                 # Project dependencies and metadata
├── uv.lock                        # Locked dependency versions
├── db.sqlite3                     # SQLite database (development)
└── README.md                      # Basic project information
```

## Application Architecture

### Django Applications

#### 1. patients/ - Patient Management
**Purpose**: Manages patient information and file uploads

**Models**:
- `Patient`: Core patient demographic information
- `File`: Patient file uploads with metadata

**Responsibilities**:
- Patient CRUD operations
- File upload and management
- Patient data validation
- File access control

#### 2. student_groups/ - Medical Observations
**Purpose**: Manages medical observations and student interactions

**Models**:
- `Note`: Patient notes and observations
- `BloodPressure`: Blood pressure measurements
- `HeartRate`: Heart rate recordings
- `BodyTemperature`: Body temperature measurements
- `ObservationManager`: Business logic for batch operations

**Responsibilities**:
- Medical observation recording
- Data validation and constraints
- Batch observation creation
- Student group management (future)

### Architectural Patterns

#### 1. Model-View-Serializer (MVS) Pattern
```
Request → URL → View → Serializer → Model → Database
                ↓
Response ← Serializer ← Model ← Database
```

#### 2. Repository Pattern (Implicit)
Models act as repositories with custom managers for complex queries.

#### 3. Service Layer Pattern
Business logic is encapsulated in model methods and managers.

## Database Design

### Entity Relationship Diagram

```
┌─────────────┐       ┌──────────────┐
│   Patient   │◄─────►│     File     │
├─────────────┤   1:N ├──────────────┤
│ id (PK)     │       │ id (PK)      │
│ first_name  │       │ patient (FK) │
│ last_name   │       │ display_name │
│ email       │       │ file         │
│ phone       │       │ created_at   │
│ birth_date  │       └──────────────┘
│ created_at  │
│ updated_at  │
└─────────────┘
       │
       │ 1:N
       ▼
┌─────────────┐
│    Note     │
├─────────────┤
│ id (PK)     │
│ patient(FK) │
│ user (FK)   │
│ content     │
│ created_at  │
│ updated_at  │
└─────────────┘
       │
       │ 1:N (same patient)
       ▼
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│BloodPressure│    │ HeartRate   │    │BodyTemp     │
├─────────────┤    ├─────────────┤    ├─────────────┤
│ id (PK)     │    │ id (PK)     │    │ id (PK)     │
│ patient(FK) │    │ patient(FK) │    │ patient(FK) │
│ user (FK)   │    │ user (FK)   │    │ user (FK)   │
│ systolic    │    │ heart_rate  │    │ temperature │
│ diastolic   │    │ created_at  │    │ created_at  │
│ created_at  │    └─────────────┘    └─────────────┘
└─────────────┘
```

### Database Tables

#### patients_patient
```sql
CREATE TABLE patients_patient (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    date_of_birth DATE NOT NULL,
    email VARCHAR(254) UNIQUE NOT NULL,
    phone_number VARCHAR(15),
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL
);
```

#### patients_file
```sql
CREATE TABLE patients_file (
    id CHAR(32) PRIMARY KEY,  -- UUID
    patient_id INTEGER NOT NULL REFERENCES patients_patient(id),
    display_name VARCHAR(255) NOT NULL,
    file VARCHAR(100) NOT NULL,
    created_at DATETIME NOT NULL
);
```

#### student_groups_note
```sql
CREATE TABLE student_groups_note (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id INTEGER NOT NULL REFERENCES patients_patient(id),
    user_id INTEGER NOT NULL REFERENCES auth_user(id),
    content TEXT NOT NULL,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL
);
```

#### Medical Observation Tables
```sql
-- Blood Pressure
CREATE TABLE student_groups_bloodpressure (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id INTEGER NOT NULL REFERENCES patients_patient(id),
    user_id INTEGER NOT NULL REFERENCES auth_user(id),
    systolic INTEGER NOT NULL,
    diastolic INTEGER NOT NULL,
    created_at DATETIME NOT NULL
);

-- Heart Rate
CREATE TABLE student_groups_heartrate (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id INTEGER NOT NULL REFERENCES patients_patient(id),
    user_id INTEGER NOT NULL REFERENCES auth_user(id),
    heart_rate INTEGER NOT NULL,
    created_at DATETIME NOT NULL
);

-- Body Temperature
CREATE TABLE student_groups_bodytemperature (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id INTEGER NOT NULL REFERENCES patients_patient(id),
    user_id INTEGER NOT NULL REFERENCES auth_user(id),
    temperature DECIMAL(4,1) NOT NULL,
    created_at DATETIME NOT NULL
);
```

### Indexes and Constraints

#### Performance Indexes
```sql
-- Patient lookups
CREATE INDEX idx_patient_email ON patients_patient(email);
CREATE INDEX idx_patient_name ON patients_patient(last_name, first_name);

-- File lookups
CREATE INDEX idx_file_patient ON patients_file(patient_id);
CREATE INDEX idx_file_created ON patients_file(created_at);

-- Observation lookups
CREATE INDEX idx_note_patient ON student_groups_note(patient_id);
CREATE INDEX idx_bp_patient ON student_groups_bloodpressure(patient_id);
CREATE INDEX idx_hr_patient ON student_groups_heartrate(patient_id);
CREATE INDEX idx_temp_patient ON student_groups_bodytemperature(patient_id);

-- Time-based queries
CREATE INDEX idx_note_created ON student_groups_note(created_at);
CREATE INDEX idx_bp_created ON student_groups_bloodpressure(created_at);
CREATE INDEX idx_hr_created ON student_groups_heartrate(created_at);
CREATE INDEX idx_temp_created ON student_groups_bodytemperature(created_at);
```

## API Architecture

### URL Structure

```
/api/
├── patients/                           # Patient management
│   ├── GET    /                       # List patients
│   ├── POST   /                       # Create patient
│   ├── GET    /{id}/                  # Get patient details
│   ├── PUT    /{id}/                  # Update patient
│   ├── PATCH  /{id}/                  # Partial update
│   ├── DELETE /{id}/                  # Delete patient
│   └── {id}/files/                    # Nested file resources
│       ├── GET    /                   # List patient files
│       ├── POST   /                   # Upload file
│       ├── GET    /{file_id}/         # Get file details
│       └── DELETE /{file_id}/         # Delete file
│
├── student-groups/                     # Medical observations
│   ├── notes/                         # Patient notes
│   │   ├── GET    /                   # List notes
│   │   ├── POST   /                   # Create note
│   │   ├── GET    /{id}/              # Get note
│   │   ├── PUT    /{id}/              # Update note
│   │   └── DELETE /{id}/              # Delete note
│   │
│   └── observations/                  # Medical measurements
│       ├── GET    /                   # Bulk observation endpoint
│       ├── POST   /                   # Create multiple observations
│       ├── blood-pressures/           # Blood pressure readings
│       ├── heart-rates/               # Heart rate readings
│       └── body-temperatures/         # Temperature readings
│
├── schema/                            # OpenAPI schema
├── docs/                              # Swagger UI
└── redoc/                             # ReDoc documentation
```

### ViewSet Architecture

#### Base ViewSet Structure
```python
class BaseViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        # Override to implement filtering
        pass
    
    def perform_create(self, serializer):
        # Override to add custom create logic
        pass
```

#### Patient ViewSet
```python
class PatientViewSet(viewsets.ModelViewSet):
    queryset = Patient.objects.all()
    serializer_class = PatientSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['first_name', 'last_name']
    search_fields = ['first_name', 'last_name', 'email']
    ordering_fields = ['created_at', 'last_name']
```

#### Nested File ViewSet
```python
class FileViewSet(mixins.RetrieveModelMixin,
                  mixins.ListModelMixin,
                  mixins.DestroyModelMixin,
                  viewsets.GenericViewSet):
    
    def get_queryset(self):
        return File.objects.filter(patient_id=self.kwargs['patient_pk'])
```

### Serializer Architecture

#### Serializer Hierarchy
```python
# Base serializer with common fields
class BaseModelSerializer(serializers.ModelSerializer):
    class Meta:
        read_only_fields = ('created_at', 'updated_at')

# Patient serializer
class PatientSerializer(BaseModelSerializer):
    full_name = serializers.SerializerMethodField()
    
    class Meta:
        model = Patient
        fields = '__all__'
    
    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}"

# Nested serializers for related data
class PatientWithFilesSerializer(PatientSerializer):
    files = FileSerializer(many=True, read_only=True)
```

## File Organization

### Upload Structure

#### File Naming Convention
```python
def upload_to(instance, filename):
    """
    Generate upload path: uploads/YYYY/MM/DD/{uuid}.{ext}
    """
    today = datetime.today().strftime("%Y/%m/%d")
    ext = filename.split(".")[-1]
    unique_filename = f"{instance.id}.{ext}"
    return os.path.join("uploads", today, unique_filename)
```

#### Directory Structure
```
media/
└── uploads/
    └── 2024/
        └── 01/
            └── 15/
                ├── 550e8400-e29b-41d4-a716-446655440000.pdf
                ├── 6ba7b810-9dad-11d1-80b4-00c04fd430c8.jpg
                └── 6ba7b811-9dad-11d1-80b4-00c04fd430c8.docx
```

### Static Files Organization
```
static/
├── admin/                    # Django admin static files
├── rest_framework/           # DRF static files
└── drf_spectacular/          # API documentation assets
```

## Configuration Management

### Settings Architecture

#### Base Settings (settings.py)
```python
# Core Django settings
BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = os.environ.get('SECRET_KEY', 'default-dev-key')
DEBUG = os.environ.get('DEBUG', 'True').lower() == 'true'
ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'drf_spectacular',
    'corsheaders',
    'patients',
    'student_groups',
]

# REST Framework configuration
REST_FRAMEWORK = {
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 10,
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
}
```

#### Environment-specific Settings
```python
# Development
if DEBUG:
    CORS_ALLOW_ALL_ORIGINS = True
    LOGGING['loggers']['django.db.backends'] = {
        'level': 'DEBUG',
        'handlers': ['console'],
    }

# Production
if not DEBUG:
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
```

### Environment Variables
```bash
# Development (.env)
DEBUG=True
SECRET_KEY=dev-secret-key
DATABASE_URL=sqlite:///db.sqlite3
ALLOWED_HOSTS=localhost,127.0.0.1

# Production (.env.production)
DEBUG=False
SECRET_KEY=production-secret-key
DATABASE_URL=postgresql://user:pass@localhost/dbname
ALLOWED_HOSTS=example.com,www.example.com
```

## Security Architecture

### Authentication & Authorization

#### Authentication Flow
```
1. User submits credentials → Django Authentication
2. Session created → Session stored in database
3. Subsequent requests → Session validation
4. API access → Permission checks
```

#### Permission Levels
```python
# View-level permissions
class PatientViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]

# Object-level permissions (future)
class PatientViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated, IsPatientOwner]
```

### Data Security

#### File Security
```python
class File(models.Model):
    # UUID primary key prevents enumeration
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    
    # Custom upload path obscures file structure
    file = models.FileField(upload_to=upload_to)
    
    def get_full_path(self):
        # Controlled file access
        return os.path.join(settings.MEDIA_ROOT, self.file.path)
```

#### Input Validation
```python
class PatientSerializer(serializers.ModelSerializer):
    def validate_email(self, value):
        if Patient.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email already exists")
        return value
    
    def validate_date_of_birth(self, value):
        if value > timezone.now().date():
            raise serializers.ValidationError("Birth date cannot be in future")
        return value
```

### CORS Configuration
```python
# Development - Allow all origins
CORS_ALLOW_ALL_ORIGINS = True

# Production - Specific origins only
CORS_ALLOWED_ORIGINS = [
    "https://yourdomain.com",
    "https://www.yourdomain.com",
]

CORS_ALLOW_CREDENTIALS = True
```

### CSRF Protection
```python
# Enabled by default for all non-API requests
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',  # CSRF protection
    # ... other middleware
]
```

## Performance Considerations

### Database Optimization

#### Query Optimization
```python
# Use select_related for foreign keys
patients = Patient.objects.select_related('user').all()

# Use prefetch_related for reverse foreign keys
patients = Patient.objects.prefetch_related('files', 'notes').all()

# Database indexes for common queries
class Meta:
    indexes = [
        models.Index(fields=['last_name', 'first_name']),
        models.Index(fields=['created_at']),
    ]
```

#### Pagination
```python
# Configured in settings
REST_FRAMEWORK = {
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 10,  # Reasonable default
}
```

### File Handling

#### Upload Limits
```python
# settings.py
FILE_UPLOAD_MAX_MEMORY_SIZE = 50 * 1024 * 1024  # 50MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 50 * 1024 * 1024   # 50MB
```

#### Media Storage
```python
# Development - Local storage
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Production - Cloud storage (future)
# DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
# AWS_STORAGE_BUCKET_NAME = 'your-bucket-name'
```

## Scalability Architecture

### Horizontal Scaling Considerations

#### Stateless Design
- Session data stored in database
- No server-side file processing
- API endpoints are stateless

#### Database Scaling
```python
# Read/write splitting (future)
DATABASE_ROUTERS = ['myapp.routers.DatabaseRouter']

# Connection pooling
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'CONN_MAX_AGE': 600,  # Connection pooling
    }
}
```

#### Caching Strategy (Future)
```python
# Redis caching
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}

# Cache API responses
@method_decorator(cache_page(60 * 15), name='list')  # 15 minutes
class PatientViewSet(viewsets.ModelViewSet):
    pass
```

---

## Summary

The DMR project follows Django best practices with a clear separation of concerns:

1. **Modular Design**: Separate apps for different functional areas
2. **RESTful API**: Standard REST endpoints with proper HTTP methods
3. **Security First**: Authentication, validation, and secure file handling
4. **Scalable Architecture**: Designed for horizontal scaling
5. **Performance Optimized**: Database indexes, pagination, and query optimization
6. **Maintainable Code**: Clear structure, documentation, and testing

This architecture provides a solid foundation for a medical records system that can grow and evolve with changing requirements.
