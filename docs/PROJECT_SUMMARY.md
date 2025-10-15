# DMR Project Summary

This document provides a comprehensive project overview, system architecture, module boundaries, permission model, and key business logic. For development standards and coding conventions, see [DEVELOPMENT_STANDARDS.md](./DEVELOPMENT_STANDARDS.md).

## 1. Project Purpose and Context

This is a Django + DRF-based Digital Medical Records (DMR) simulation backend for teaching practice: students record observations and notes, and initiate lab requests under shared group accounts; instructors review and generate statistics.

**Key Characteristics:**

- **Tech Stack**: Django 5.2+ with Django REST Framework
- **Database**: SQLite (default `data/db.sqlite3`)
- **Authentication**: DRF Token + Session (see `REST_FRAMEWORK` in `dmr/settings.py`)
- **API Documentation**: Swagger/OpenAPI at `/schema/swagger-ui/`
- **Package Manager**: `uv` (recommended)

For setup and running instructions, see `README.md` in the root directory.

## 2. Routing and Application Boundaries

- Top-level Routes (`dmr/urls.py`):
  - `api/` -> `core.urls`
  - `api/patients/` -> Patient and File APIs (`patients`)
  - `api/student-groups/` -> Observations and Lab Requests (`student_groups`)
  - `api/instructors/` -> Instructor-side Management (`instructors`)
  - Swagger/OpenAPI: `/schema/` and `/schema/swagger-ui/`

- Application Boundaries and Responsibilities:
  - core: General permissions and authentication serializers (`core.permissions`, `core.serializers`).
  - patients: `Patient`, `File`, `GoogleFormLink` models and views; upload, view, and manage files; manage Google Form links (read-only for students, full CRUD for instructors).
  - student_groups: Observation models (Note, vital signs, etc.), request models (`ImagingRequest`, `BloodTestRequest`, etc.), bulk creation API (`ObservationsViewSet`).
  - instructors: Full management of diagnostic requests (`ImagingRequest`, `BloodTestRequest`) by instructors, to-do lists, statistics, and Google Form management.

## 3. Permission Model and Access Control

### 3.1 Role Overview

The system defines three roles (in `core/context.py` as `Role` enum):

- **admin**: Full system access (superusers)
- **instructor**: Teaching staff with management capabilities
- **student**: Student group shared accounts with restricted access

Role determination is based on Django Group membership and superuser status.

### 3.2 Resource-Based Access Control

The system follows RBAC (Role-Based Access Control) principles. Each resource has specific permission rules:

**Patient and File Management:**

- `PatientPermission`: Students read-only; instructors and admins have full CRUD.
- `FileAccessPermission`: Admins/instructors access all files; students access is granted via either (a) `ApprovedFile` linked to their completed requests, or (b) manual releases recorded in `ApprovedFile.released_to_user`; access may be restricted by `page_range`.
- `FileManagementPermission`: Only instructors and admins can manage files (upload, update, delete).

**Observation Data:**

- `ObservationPermission`: Students can only CRUD their own group's records (enforced by `obj.user == request.user`); instructors have read-only access; admins have full access.

**Investigation Requests:**

- `InvestigationRequestPermission`: Students can create, view, update, and delete their own requests (ownership checked); admins have full access.
- `InstructorManagementPermission`: Instructors can manage all requests via dedicated management endpoints; students have no access to these endpoints.

**Key Design Principles:**

- All permissions are named after resources, not roles (e.g., `PatientPermission`, not `InstructorPermission`).
- Method-level control via `role_permissions` dict in each permission class.
- Object-level control via `has_object_permission` for ownership validation.

For permission development guidelines, see [DEVELOPMENT_STANDARDS.md](./DEVELOPMENT_STANDARDS.md#2-permission-development-guidelines).

## 4. Key Models and Business Flow

- Student Groups and User Relationships

  - Login and Ownership: Teaching adopts a "student group shared account" model, where one student group corresponds to one Django user (User) account for login; the `user` foreign key in each model represents the operator (i.e., the shared account of that group).
  - Definition of "Own Records": Refers to records of the currently authenticated user; in shared account mode, this is equivalent to "records created by or belonging to this group."
  - Permission Impact:
    - Observation Data: `ObservationPermission` performs an object-level check `obj.user == request.user`, so students can only CRUD their group's records; instructors have read-only access to observations, and admin has full access.
    - Diagnostic Requests: Student-side request views are restricted to `user=self.request.user`; instructor-side can manage all requests.
    - File Access: Student access is allowed when an `ApprovedFile` exists associated with a completed request (e.g., `imaging_request__user=request.user, imaging_request__status="completed"`) or when a manual release exists (`released_to_user=request.user`); access can be restricted by `page_range`. Instructors/admins can access all.
  - Endpoint Practice:
    - Student-side creation APIs should fix `user=request.user` at the view layer (not trusting `user` in the request body) to prevent unauthorized access. `LabRequest` is currently enforced; `Observations` creation still requires `user` to be passed, the calling end must pass the current user, which can be overridden at the view layer for further convergence.
    - Query APIs for students must filter based on `request.user` to prevent reading data from other groups.
  - Testing Key Points:
    - Use two different student users to simulate different groups and verify object-level permission denial for cross-group access/modification.
    - Verify that "different members of the same group" behave identically to the same `request.user` on the backend.

- Patients and Files (`patients/models.py`, `patients/views.py`):
  - `Patient`: Basic information model.
  - `File`: File record with optional categorization; `requires_pagination` controls whether "page-based authorization" is enabled. Override `delete()` to remove files from disk.
  - File Storage: `file = models.FileField(upload_to="upload_to")`, i.e., the path is `MEDIA_ROOT/upload_to/`.
  - File Viewing: `FileViewSet.view` supports PDF output for specified pages; authorized page range comes from `ApprovedFile.page_range` via completed diagnostic requests or manual releases.
  - Upload: `PatientViewSet.upload_file` is an action route; controlled by `PatientPermission`, students cannot upload.

- Observations and Bulk Creation (`student_groups`):
  - Models: `Note`, `BloodPressure`, `HeartRate`, `BodyTemperature`, `RespiratoryRate`, `BloodSugar`, `OxygenSaturation`, all containing `patient` and `user` foreign keys.
  - Validation: `ObservationValidator` is executed in model `clean()` and serializer `validate()`.
  - Bulk Creation: `ObservationsViewSet.create` calls `ObservationManager.create_observations`, which transactionally creates multiple records and returns a serialized data dictionary.

- Diagnostic Requests (`ImagingRequest`, `BloodTestRequest`, etc.):
  - Student-side: Request views in `student_groups.views` only operate on the current user's requests.
  - Instructor-side: Request views in `instructors.views` provide full CRUD functionality; status updates are constrained by serializer rules (e.g., `ImagingRequestStatusUpdateSerializer`); can manage approved files.
  - Instructor-side: Request views in `instructors.views` provide full CRUD functionality; status updates are constrained by serializer rules (e.g., `ImagingRequestStatusUpdateSerializer`); can manage approved files. Instructors can also manually release file access to student group accounts without a request using the File API.
  - Additional request types: `MedicationOrder`, `DischargeSummary`, etc., follow similar patterns.
  - Dashboard views provide basic statistics on request status and completion.

- Google Forms (`GoogleFormLink` in `patients/models.py`):
  - Model: `GoogleFormLink` stores form title, URL, description, display order, and active status.
  - Student/Patient Access: Read-only access to active forms via `GET /api/patients/google-forms/`.
  - Instructor Management: Full CRUD access via `GET/POST/PUT/PATCH/DELETE /api/instructors/google-forms/` endpoints.
  - Authorization: Forms are managed by instructors using `InstructorManagementPermission`; students have read-only access.
  - Display: Forms are ordered by `display_order` and can be toggled active/inactive.

## 5. Data Security and File Access Control

- **File Types**: Only files marked `requires_pagination=True` are allowed to configure `page_range` (usually limited to PDF).
- **Access Control**: `FileAccessPermission` + `ApprovedFile` + `LabRequest(status=completed)` collectively restrict student access to file pages.
- **Sensitive Information**: Example and test data should avoid real PII; media sample files are for teaching demonstration only.

## 6. Testing Key Points

Permission test cases should cover:

- Positive and negative scenarios for admin/instructor/student roles
- Object-level permissions (e.g., `obj.user == request.user`)
- Cross-group access denial for student accounts
- File access authorization based on approved requests

For detailed testing standards and conventions, see [DEVELOPMENT_STANDARDS.md](./DEVELOPMENT_STANDARDS.md#5-testing-standards).

## 7. Quick Reference

**Key Configuration Files:**

- Project Settings: `dmr/settings.py`
- URL Routing: `dmr/urls.py`
- Permissions: `core/permissions.py`
- Base Serializers: `core/serializers.py`

**Module Locations:**

- **Patients & Files**: `patients/` (models, views, serializers)
- **Student Groups**: `student_groups/` (observations, lab requests, validators)
- **Instructors**: `instructors/` (management views, statistics)
- **Tests**: `tests/` (integration tests) + per-app `tests.py` (unit tests)
- **Documentation**: `docs/`

**Related Documentation:**

- Setup Guide: [README.md](../README.md)
- Development Standards: [DEVELOPMENT_STANDARDS.md](./DEVELOPMENT_STANDARDS.md)
- Docker Guide: [DOCKER_GUIDE.md](./DOCKER_GUIDE.md)
- Development Guide: [DEVELOPMENT_GUIDE.md](./DEVELOPMENT_GUIDE.md)

## 8. New: Manual File Release (Instructor)

Instructors can grant student group accounts access to patient documents without a corresponding request.

- API endpoints:
  - Instructor list student groups: `GET /api/instructors/student-groups/` → returns user accounts in the student group role.
  - File manual release: `POST /api/patients/patients/{patient_id}/files/{file_id}/release/` with body `{ "student_group_ids": [<userId>, ...], "page_range": "1-3,5"? }`. `page_range` is required for files with `requires_pagination=True`.
- Data model: Manual releases are written to `student_groups.ApprovedFile` with `released_to_user` and optional `page_range`. A unique constraint prevents duplicate manual releases per (file, user).
- Authorization effects: Students gain `FileAccessPermission` for the released file; for PDFs with pagination, access is limited to the specified `page_range`.
