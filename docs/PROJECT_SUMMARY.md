# DMR Project Overview and Development Specification

This document provides a project overview, module boundaries, permission model, and comprehensive development specifications and process conventions.

## 1. Project Purpose and Operation

This is a Django + DRF-based Electronic Medical Record (EMR) simulation backend for teaching practice: students record observations and notes, and initiate lab requests under shared group accounts; instructors review and generate statistics.

Key Operating Points (see `README.md` in the root directory for details):

- Dependency Management: `uv` is recommended (`uv sync`), traditional venv+pip is also an option.
- Database: SQLite (default `db.sqlite3`).
- Startup: `uv run python manage.py runserver`; Swagger: `/schema/swagger-ui/`.
- Authentication: DRF Token + Session (see `REST_FRAMEWORK` in `dmr/settings.py`).

## 2. Routing and Application Boundaries

- Top-level Routes (`dmr/urls.py`):
  - `api/` -> `core.urls`
  - `api/patients/` -> Patient and File APIs (`patients`)
  - `api/student-groups/` -> Observations and Lab Requests (`student_groups`)
  - `api/instructors/` -> Instructor-side Management (`instructors`)
  - Swagger/OpenAPI: `/schema/` and `/schema/swagger-ui/`

- Application Boundaries and Responsibilities:
  - core: General permissions and authentication serializers (`core.permissions`, `core.serializers`).
  - patients: `Patient`, `File` models and views; upload, view, and manage files.
  - student_groups: Observation models (Note, vital signs, etc.), `LabRequest`, bulk creation API (`ObservationsViewSet`).
  - instructors: Full management of `LabRequest` by instructors, to-do lists, and statistics.

## 3. Permission Model

- Role Constants: `admin`, `instructor`, `student` (`core/permissions.py`).
- Base Class: `BaseRolePermission` + `role_permissions` controls method-level permissions; admin has full access unless explicitly restricted.
- Permission Classes and Key Points:
  - `PatientPermission`: student read-only; instructor full; admin full.
  - `ObservationPermission`: student can only CRUD their own records (object-level check `obj.user == request.user`); instructor read-only; admin full.
  - `LabRequestPermission` (Student-side): student can create and read their own requests; instructor read-only (full CRUD on instructor-side).
  - `InstructorOnlyPermission`: only instructor/admin can access (instructor-side).
  - `FileAccessPermission`: admin/instructor can access all files; student can only access `ApprovedFile` bound to their "completed" `LabRequest`, and is restricted by `page_range`.
  - `FileManagementPermission`: only instructor/admin can manage files (CRUD).

Usage Requirement: New views must explicitly set `permission_classes`.

## 4. Key Models and Business Flow

- Student Groups and User Relationships

  - Login and Ownership: Teaching adopts a "student group shared account" model, where one student group corresponds to one Django user (User) account for login; the `user` foreign key in each model represents the operator (i.e., the shared account of that group).
  - Definition of "Own Records": Refers to records of the currently authenticated user; in shared account mode, this is equivalent to "records created by or belonging to this group."
  - Permission Impact:
    - Observation Data: `ObservationPermission` performs an object-level check `obj.user == request.user`, so students can only CRUD their group's records; instructors have read-only access to observations, and admin has full access.
    - Lab Requests: Student-side `LabRequestViewSet.get_queryset()` is restricted to `user=self.request.user`; instructor-side can manage all.
    - File Access: Student file access requires the existence of `ApprovedFile(file=obj, lab_request__user=request.user, lab_request__status="completed")`, and is restricted by `page_range`; instructor/admin can access all.
  - Endpoint Practice:
    - Student-side creation APIs should fix `user=request.user` at the view layer (not trusting `user` in the request body) to prevent unauthorized access. `LabRequest` is currently enforced; `Observations` creation still requires `user` to be passed, the calling end must pass the current user, which can be overridden at the view layer for further convergence.
    - Query APIs for students must filter based on `request.user` to prevent reading data from other groups.
  - Testing Key Points:
    - Use two different student users to simulate different groups and verify object-level permission denial for cross-group access/modification.
    - Verify that "different members of the same group" behave identically to the same `request.user` on the backend.

- Patients and Files (`patients/models.py`, `patients/views.py`):
  - `Patient`: Basic information model.
  - `File`: File record; `requires_pagination` controls whether "page-based authorization" is enabled. Override `delete()` to remove files from disk.
  - File Storage: `file = models.FileField(upload_to="upload_to")`, i.e., the path is `MEDIA_ROOT/upload_to/`.
  - File Viewing: `FileViewSet.view` supports PDF output for specified pages; authorized page range comes from `ApprovedFile.page_range` and completed `LabRequest`.
  - Upload: `PatientViewSet.upload_file` is an action route; controlled by `PatientPermission`, students cannot upload.

- Observations and Bulk Creation (`student_groups`):
  - Models: `Note`, `BloodPressure`, `HeartRate`, `BodyTemperature`, `RespiratoryRate`, `BloodSugar`, `OxygenSaturation`, all containing `patient` and `user` foreign keys.
  - Validation: `ObservationValidator` is executed in model `clean()` and serializer `validate()`.
  - Bulk Creation: `ObservationsViewSet.create` calls `ObservationManager.create_observations`, which transactionally creates multiple records and returns a serialized data dictionary.

- Lab Requests (`LabRequest`):
  - Student-side: `student_groups.views.LabRequestViewSet` only operates on the current user's requests.
  - Instructor-side: `instructors.views.LabRequestViewSet` full CRUD; status updates are constrained by `LabRequestStatusUpdateSerializer` rules; can manage `ApprovedFile`.
  - Dashboard: `DashboardViewSet` provides basic statistics.

## 5. Test Organization and Naming

- Location:
  - Centralized directory `tests/`: Login, cross-app integration/end-to-end tests.
  - Within app: Unit tests can be placed (e.g., `patients/tests.py`, `instructors/tests.py`, etc.).
- Naming:
  - Unit tests: `test_<feature>.py` or centralized in the app's `tests.py`.
  - Integration tests: `test_<feature>_integration.py` (usually in `tests/`).
- Basic Conventions:
  - Use DRF's `APIClient` for API testing.
  - Tests involving file operations use `override_settings(MEDIA_ROOT=tmpdir)` to isolate the environment and clean up afterwards.
  - Permission test cases should cover both positive and negative scenarios for admin/instructor/student.
  - Assert response structure and status codes; validate object-level permissions (e.g., `obj.user == request.user`).

## 6. Code Style and Naming

- Naming: Variables/functions `snake_case`; classes `PascalCase`; constants `UPPER_SNAKE_CASE`; private `_leading_underscore`.
- Permission Class Naming: `<FeatureName>Permission` (e.g., `PatientPermission`, `FileAccessPermission`).
- URL Naming: `<app>-<action>` (e.g., `patient-list`, `patient-detail`, `file-view`).
- Documentation: Modules, classes, methods provide Chinese docstrings; explain purpose, parameters, return values, and exceptions.
- Serializers: Common timestamp fields are handled by `core.serializers.BaseModelSerializer`.

## 7. Branching and Commits

- Branch Naming: `feature/<name>`, `fix/<name>`, `chore/<name>` (e.g., current branch `feature/instructor`).
- Commit Messages: Recommended to follow Conventional Commits (`feat: …`, `fix: …`, `docs: …`, `refactor: …`, `test: …`, `chore: …`).
- PR Conventions: Describe motivation, changes, verification methods, and scope of impact; link to issues; at least one reviewer.

## 8. Development Process

1) Requirements Analysis: Understand data relationships and permission boundaries; confirm scope of impact.
2) Implementation:
   - Follow existing patterns and styles; prioritize minimal changes within existing files.
   - New endpoints explicitly declare `permission_classes`; add OpenAPI annotations (`extend_schema`).
   - Pre-validate serializers to prevent business exceptions from resulting in 500 errors; input errors should primarily return 400.
3) Testing: New features should be accompanied by unit tests and at least 1 boundary/negative case; regression test existing tests.
4) Self-check: Local run, basic smoke test; check permissions and response structure.

## 9. Quality Gates and Tools

- Build: Buildable; no syntax/import errors.
- Lint/Type: Keep imports clean; avoid unused code; if type annotations are introduced, ensure basic checks pass.
- Testing: Can run independently and pass; avoid reliance on external states (network, real media).
- Documentation: Update `docs/` and relevant sections in this document; examples consistent with code.
- API Documentation: `drf-spectacular` is enabled (`SCHEMA_PATH_PREFIX = "/api"`).
- CORS/Authentication: Cross-origin allowed during development; configuration needs to be tightened for production.

## 10. Data and Security

- File Types: Only files marked `requires_pagination=True` are allowed to configure `page_range` (usually limited to PDF).
- Access Control: `FileAccessPermission` + `ApprovedFile` + `LabRequest(status=completed)` collectively restrict student access to file pages.
- Sensitive Information: Example and test data should avoid real PII; media sample files are for teaching demonstration only.

## 11. Migrations and Dependencies

- Migrations: Model changes require generating and committing migration files; pay attention to default values and data compatibility.
- Dependencies: Managed uniformly via uv; commit `pyproject.toml` and `uv.lock`.

## 12. Quick Locator

- Configuration: `dmr/settings.py`
- Permissions: `core/permissions.py`
- Patients/Files: `patients/models.py`, `patients/views.py`, `patients/serializers.py`
- Student Groups: `student_groups/models.py`, `student_groups/serializers.py`, `student_groups/views.py`, `student_groups/validators.py`
- Instructor-side: `instructors/views.py`, `instructors/serializers.py`
