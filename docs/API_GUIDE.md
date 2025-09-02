# DMR API Development Guide

## Table of Contents
1. [API Overview](#api-overview)
2. [Authentication](#authentication)
3. [API Endpoints](#api-endpoints)
4. [Request/Response Format](#requestresponse-format)
5. [Error Handling](#error-handling)
6. [Pagination](#pagination)
7. [Filtering and Search](#filtering-and-search)
8. [File Upload](#file-upload)
9. [API Examples](#api-examples)
10. [Testing APIs](#testing-apis)

## API Overview

The DMR API is built using Django REST Framework and provides comprehensive endpoints for managing digital medical records. The API follows RESTful principles and returns JSON responses.

### Base URL
```
http://127.0.0.1:8000/api/
```

### API Version
Current version: `v1` (implicit)

### Content Type
All requests should use `application/json` content type unless uploading files.

## Authentication

### Session Authentication (Default)
The API uses Django's session authentication for web browsers:

```bash
# Login to get session cookie
curl -X POST http://127.0.0.1:8000/api-auth/login/ \
     -H "Content-Type: application/x-www-form-urlencoded" \
     -d "username=your_username&password=your_password" \
     -c cookies.txt

# Use session cookie for subsequent requests
curl -b cookies.txt http://127.0.0.1:8000/api/patients/
```

### Token Authentication (Optional)
For API clients, you can configure token authentication:

```python
# In settings.py
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.TokenAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
}

# Generate token for user
from rest_framework.authtoken.models import Token
token = Token.objects.create(user=user)
```

```bash
# Use token in requests
curl -H "Authorization: Token your_token_here" \
     http://127.0.0.1:8000/api/patients/
```

## API Endpoints

### Patients API

#### List Patients
```http
GET /api/patients/
```

**Response:**
```json
{
  "count": 2,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 1,
      "first_name": "John",
      "last_name": "Doe",
      "date_of_birth": "1990-01-01",
      "email": "john@example.com",
      "phone_number": "+1234567890",
      "created_at": "2024-01-01T10:00:00Z",
      "updated_at": "2024-01-01T10:00:00Z"
    }
  ]
}
```

#### Create Patient
```http
POST /api/patients/
Content-Type: application/json

{
  "first_name": "Jane",
  "last_name": "Smith",
  "date_of_birth": "1985-05-15",
  "email": "jane@example.com",
  "phone_number": "+0987654321"
}
```

#### Get Patient Details
```http
GET /api/patients/{id}/
```

#### Update Patient
```http
PUT /api/patients/{id}/
PATCH /api/patients/{id}/
```

#### Delete Patient
```http
DELETE /api/patients/{id}/
```

### Patient Files API

#### List Patient Files
```http
GET /api/patients/{patient_id}/files/
```

#### Upload Patient File
```http
POST /api/patients/{patient_id}/files/
Content-Type: multipart/form-data

file: [binary file data]
display_name: "Medical Report 2024"
```

#### Get File Details
```http
GET /api/patients/{patient_id}/files/{file_id}/
```

#### Delete File
```http
DELETE /api/patients/{patient_id}/files/{file_id}/
```

### Student Groups API

#### Notes

##### List Notes
```http
GET /api/student-groups/notes/
```

##### Create Note
```http
POST /api/student-groups/notes/
Content-Type: application/json

{
  "patient": 1,
  "content": "Patient showed improvement in mobility exercises."
}
```

#### Medical Observations

##### Blood Pressure
```http
# List blood pressure readings
GET /api/student-groups/observations/blood-pressures/

# Create blood pressure reading
POST /api/student-groups/observations/blood-pressures/
{
  "patient": 1,
  "systolic": 120,
  "diastolic": 80
}
```

##### Heart Rate
```http
# List heart rate readings
GET /api/student-groups/observations/heart-rates/

# Create heart rate reading
POST /api/student-groups/observations/heart-rates/
{
  "patient": 1,
  "heart_rate": 72
}
```

##### Body Temperature
```http
# List temperature readings
GET /api/student-groups/observations/body-temperatures/

# Create temperature reading
POST /api/student-groups/observations/body-temperatures/
{
  "patient": 1,
  "temperature": "36.5"
}
```

##### Bulk Observations
```http
# Create multiple observations at once
POST /api/student-groups/observations/
{
  "patient": 1,
  "blood_pressure": {
    "systolic": 120,
    "diastolic": 80
  },
  "heart_rate": {
    "heart_rate": 72
  },
  "body_temperature": {
    "temperature": "36.5"
  }
}
```

## Request/Response Format

### Standard Response Format

#### Success Response
```json
{
  "id": 1,
  "field1": "value1",
  "field2": "value2",
  "created_at": "2024-01-01T10:00:00Z",
  "updated_at": "2024-01-01T10:00:00Z"
}
```

#### List Response with Pagination
```json
{
  "count": 100,
  "next": "http://127.0.0.1:8000/api/patients/?page=2",
  "previous": null,
  "results": [
    {
      "id": 1,
      "field1": "value1"
    }
  ]
}
```

### Date/Time Format
All dates and times use ISO 8601 format:
- **Date**: `YYYY-MM-DD` (e.g., `2024-01-01`)
- **DateTime**: `YYYY-MM-DDTHH:MM:SSZ` (e.g., `2024-01-01T10:00:00Z`)

### Field Validation

#### Required Fields
```json
{
  "first_name": "Required",
  "last_name": "Required",
  "date_of_birth": "Required",
  "email": "Required and must be unique"
}
```

#### Field Constraints
- **first_name/last_name**: Max 100 characters
- **email**: Must be valid email format and unique
- **phone_number**: Max 15 characters, optional
- **date_of_birth**: Cannot be in the future

## Error Handling

### HTTP Status Codes

| Status Code | Description |
|-------------|-------------|
| 200 | OK - Request successful |
| 201 | Created - Resource created successfully |
| 204 | No Content - Request successful (DELETE) |
| 400 | Bad Request - Validation errors |
| 401 | Unauthorized - Authentication required |
| 403 | Forbidden - Permission denied |
| 404 | Not Found - Resource not found |
| 405 | Method Not Allowed - HTTP method not allowed |
| 500 | Internal Server Error - Server error |

### Error Response Format

#### Validation Errors (400)
```json
{
  "field_name": [
    "This field is required."
  ],
  "email": [
    "Patient with this email already exists."
  ]
}
```

#### Authentication Error (401)
```json
{
  "detail": "Authentication credentials were not provided."
}
```

#### Permission Error (403)
```json
{
  "detail": "You do not have permission to perform this action."
}
```

#### Not Found Error (404)
```json
{
  "detail": "Not found."
}
```

## Pagination

### Default Pagination
- **Page Size**: 10 items per page
- **Type**: Page number pagination

### Pagination Parameters
```http
GET /api/patients/?page=2&page_size=20
```

### Pagination Response
```json
{
  "count": 100,
  "next": "http://127.0.0.1:8000/api/patients/?page=3",
  "previous": "http://127.0.0.1:8000/api/patients/?page=1",
  "results": [...]
}
```

### Custom Page Size
```http
GET /api/patients/?page_size=50
```
Maximum page size: 100

## Filtering and Search

### Search
Search across multiple fields:
```http
GET /api/patients/?search=john
```

### Filtering
Filter by specific fields:
```http
# Filter by first name
GET /api/patients/?first_name=John

# Filter by multiple fields
GET /api/patients/?first_name=John&last_name=Doe
```

### Ordering
```http
# Order by creation date (newest first)
GET /api/patients/?ordering=-created_at

# Order by last name
GET /api/patients/?ordering=last_name

# Multiple ordering
GET /api/patients/?ordering=last_name,first_name
```

### Date Range Filtering
```http
# Observations after specific date
GET /api/student-groups/observations/blood-pressures/?created_at__gte=2024-01-01

# Date range
GET /api/student-groups/observations/blood-pressures/?created_at__range=2024-01-01,2024-01-31
```

## File Upload

### Supported File Types
- Images: JPEG, PNG, GIF
- Documents: PDF, DOC, DOCX
- Medical files: DICOM (if configured)

### File Size Limits
- Maximum file size: 50MB
- Maximum files per patient: 100

### Upload Example
```bash
curl -X POST \
  http://127.0.0.1:8000/api/patients/1/files/ \
  -H "Authorization: Token your_token" \
  -F "file=@/path/to/file.pdf" \
  -F "display_name=Medical Report"
```

### File Response
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "patient": 1,
  "display_name": "Medical Report",
  "file": "/media/uploads/2024/01/01/550e8400-e29b-41d4-a716-446655440000.pdf",
  "created_at": "2024-01-01T10:00:00Z"
}
```

## API Examples

### Complete Patient Management Workflow

#### 1. Create a Patient
```python
import requests

# Login
session = requests.Session()
login_data = {'username': 'admin', 'password': 'your_password'}
session.post('http://127.0.0.1:8000/api-auth/login/', data=login_data)

# Create patient
patient_data = {
    'first_name': 'Alice',
    'last_name': 'Johnson',
    'date_of_birth': '1992-03-15',
    'email': 'alice@example.com',
    'phone_number': '+1555123456'
}
response = session.post('http://127.0.0.1:8000/api/patients/', json=patient_data)
patient = response.json()
print(f"Created patient: {patient['id']}")
```

#### 2. Upload Patient File
```python
# Upload file
files = {'file': open('medical_report.pdf', 'rb')}
data = {'display_name': 'Initial Medical Report'}
response = session.post(
    f"http://127.0.0.1:8000/api/patients/{patient['id']}/files/",
    files=files,
    data=data
)
file_info = response.json()
print(f"Uploaded file: {file_info['id']}")
```

#### 3. Record Medical Observations
```python
# Record blood pressure
bp_data = {
    'patient': patient['id'],
    'systolic': 125,
    'diastolic': 82
}
response = session.post(
    'http://127.0.0.1:8000/api/student-groups/observations/blood-pressures/',
    json=bp_data
)

# Record heart rate
hr_data = {
    'patient': patient['id'],
    'heart_rate': 68
}
response = session.post(
    'http://127.0.0.1:8000/api/student-groups/observations/heart-rates/',
    json=hr_data
)

# Record temperature
temp_data = {
    'patient': patient['id'],
    'temperature': '36.8'
}
response = session.post(
    'http://127.0.0.1:8000/api/student-groups/observations/body-temperatures/',
    json=temp_data
)
```

#### 4. Add Patient Note
```python
note_data = {
    'patient': patient['id'],
    'content': 'Patient reports feeling better after medication adjustment. Vital signs are stable.'
}
response = session.post(
    'http://127.0.0.1:8000/api/student-groups/notes/',
    json=note_data
)
```

### Batch Operations Example

#### Create Multiple Observations
```python
# Bulk observation creation
observations_data = {
    'patient': patient['id'],
    'blood_pressure': {
        'systolic': 118,
        'diastolic': 76
    },
    'heart_rate': {
        'heart_rate': 74
    },
    'body_temperature': {
        'temperature': '36.6'
    }
}
response = session.post(
    'http://127.0.0.1:8000/api/student-groups/observations/',
    json=observations_data
)
```

### Data Retrieval Examples

#### Get Patient with Recent Observations
```python
# Get patient details
patient_response = session.get(f'http://127.0.0.1:8000/api/patients/{patient["id"]}/')
patient_data = patient_response.json()

# Get recent blood pressure readings
bp_response = session.get(
    'http://127.0.0.1:8000/api/student-groups/observations/blood-pressures/',
    params={
        'patient': patient['id'],
        'ordering': '-created_at',
        'page_size': 5
    }
)
recent_bp = bp_response.json()

# Get patient files
files_response = session.get(f'http://127.0.0.1:8000/api/patients/{patient["id"]}/files/')
files = files_response.json()

print(f"Patient: {patient_data['first_name']} {patient_data['last_name']}")
print(f"Recent BP readings: {len(recent_bp['results'])}")
print(f"Total files: {files['count']}")
```

## Testing APIs

### Using curl

#### Basic CRUD Operations
```bash
# Login and save cookies
curl -X POST http://127.0.0.1:8000/api-auth/login/ \
     -d "username=admin&password=your_password" \
     -c cookies.txt

# Create patient
curl -X POST http://127.0.0.1:8000/api/patients/ \
     -H "Content-Type: application/json" \
     -b cookies.txt \
     -d '{
       "first_name": "Test",
       "last_name": "Patient",
       "date_of_birth": "1990-01-01",
       "email": "test@example.com"
     }'

# List patients
curl -X GET http://127.0.0.1:8000/api/patients/ \
     -H "Accept: application/json" \
     -b cookies.txt

# Get patient details
curl -X GET http://127.0.0.1:8000/api/patients/1/ \
     -H "Accept: application/json" \
     -b cookies.txt

# Update patient
curl -X PATCH http://127.0.0.1:8000/api/patients/1/ \
     -H "Content-Type: application/json" \
     -b cookies.txt \
     -d '{"phone_number": "+1234567890"}'

# Delete patient
curl -X DELETE http://127.0.0.1:8000/api/patients/1/ \
     -b cookies.txt
```

#### File Upload Testing
```bash
# Upload file
curl -X POST http://127.0.0.1:8000/api/patients/1/files/ \
     -b cookies.txt \
     -F "file=@test_file.pdf" \
     -F "display_name=Test Document"
```

### Using HTTPie

#### Installation
```bash
pip install httpie
```

#### Basic Operations
```bash
# Login
http POST http://127.0.0.1:8000/api-auth/login/ \
     username=admin password=your_password \
     --session=dmr

# Create patient
http POST http://127.0.0.1:8000/api/patients/ \
     --session=dmr \
     first_name=John last_name=Doe \
     date_of_birth=1985-06-15 \
     email=john@example.com

# List patients with search
http GET http://127.0.0.1:8000/api/patients/ \
     --session=dmr \
     search==john

# Create observation
http POST http://127.0.0.1:8000/api/student-groups/observations/blood-pressures/ \
     --session=dmr \
     patient:=1 systolic:=120 diastolic:=80
```

### Using Postman

#### Environment Setup
1. Create new environment
2. Add variables:
   - `base_url`: `http://127.0.0.1:8000`
   - `token`: (if using token auth)

#### Collection Structure
```
DMR API Tests/
├── Authentication/
│   ├── Login
│   └── Get Current User
├── Patients/
│   ├── List Patients
│   ├── Create Patient
│   ├── Get Patient
│   ├── Update Patient
│   └── Delete Patient
├── Files/
│   ├── Upload File
│   ├── List Files
│   └── Delete File
└── Observations/
    ├── Blood Pressure/
    ├── Heart Rate/
    └── Temperature/
```

#### Pre-request Scripts
```javascript
// Auto-login for requests
if (!pm.environment.get("auth_token")) {
    pm.sendRequest({
        url: pm.environment.get("base_url") + "/api-auth/login/",
        method: 'POST',
        body: {
            mode: 'formdata',
            formdata: [
                {key: 'username', value: 'admin'},
                {key: 'password', value: 'your_password'}
            ]
        }
    }, function (err, response) {
        if (!err) {
            pm.environment.set("auth_token", response.headers.get("Set-Cookie"));
        }
    });
}
```

### Automated Testing with Python

#### Unit Tests for API
```python
# tests/test_api.py
import pytest
from rest_framework.test import APIClient
from django.contrib.auth.models import User
from patients.models import Patient

@pytest.fixture
def api_client():
    return APIClient()

@pytest.fixture
def user():
    return User.objects.create_user(
        username='testuser',
        password='testpass123'
    )

@pytest.fixture
def authenticated_client(api_client, user):
    api_client.force_authenticate(user=user)
    return api_client

def test_create_patient(authenticated_client):
    data = {
        'first_name': 'Jane',
        'last_name': 'Doe',
        'date_of_birth': '1990-01-01',
        'email': 'jane@example.com'
    }
    response = authenticated_client.post('/api/patients/', data)
    assert response.status_code == 201
    assert response.data['first_name'] == 'Jane'

def test_list_patients(authenticated_client):
    Patient.objects.create(
        first_name='John',
        last_name='Smith',
        date_of_birth='1985-05-15',
        email='john@example.com'
    )
    response = authenticated_client.get('/api/patients/')
    assert response.status_code == 200
    assert response.data['count'] == 1
```

#### Integration Tests
```python
# tests/test_integration.py
import pytest
from rest_framework.test import APIClient
from django.core.files.uploadedfile import SimpleUploadedFile

def test_complete_patient_workflow(authenticated_client):
    # Create patient
    patient_data = {
        'first_name': 'Alice',
        'last_name': 'Johnson',
        'date_of_birth': '1992-03-15',
        'email': 'alice@example.com'
    }
    patient_response = authenticated_client.post('/api/patients/', patient_data)
    patient_id = patient_response.data['id']
    
    # Upload file
    test_file = SimpleUploadedFile(
        "test.txt",
        b"file_content",
        content_type="text/plain"
    )
    file_response = authenticated_client.post(
        f'/api/patients/{patient_id}/files/',
        {'file': test_file, 'display_name': 'Test File'}
    )
    assert file_response.status_code == 201
    
    # Record observations
    bp_data = {'patient': patient_id, 'systolic': 120, 'diastolic': 80}
    bp_response = authenticated_client.post(
        '/api/student-groups/observations/blood-pressures/',
        bp_data
    )
    assert bp_response.status_code == 201
    
    # Add note
    note_data = {'patient': patient_id, 'content': 'Test note'}
    note_response = authenticated_client.post(
        '/api/student-groups/notes/',
        note_data
    )
    assert note_response.status_code == 201
```

### API Documentation Testing

#### Swagger/OpenAPI Testing
```python
# Test API schema
def test_api_schema():
    client = APIClient()
    response = client.get('/schema/')
    assert response.status_code == 200
    assert 'openapi' in response.data

# Test Swagger UI
def test_swagger_ui():
    client = APIClient()
    response = client.get('/schema/swagger-ui/')
    assert response.status_code == 200
```

---

## Quick Reference

### Common Endpoints
```
GET    /api/patients/                    # List patients
POST   /api/patients/                    # Create patient
GET    /api/patients/{id}/               # Get patient
PUT    /api/patients/{id}/               # Update patient
DELETE /api/patients/{id}/               # Delete patient

GET    /api/patients/{id}/files/         # List patient files
POST   /api/patients/{id}/files/         # Upload file

POST   /api/student-groups/observations/ # Bulk observations
GET    /api/student-groups/notes/        # List notes
POST   /api/student-groups/notes/        # Create note
```

### HTTP Status Codes
- `200` - OK
- `201` - Created
- `204` - No Content
- `400` - Bad Request
- `401` - Unauthorized
- `403` - Forbidden
- `404` - Not Found
- `500` - Server Error

### Authentication Header
```
Authorization: Token your_token_here
```

### Content Types
- `application/json` - For JSON data
- `multipart/form-data` - For file uploads
- `application/x-www-form-urlencoded` - For form data
