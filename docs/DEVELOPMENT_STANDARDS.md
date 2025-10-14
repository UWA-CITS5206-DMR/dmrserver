# DMR Development Standards and Coding Conventions

This guide defines the project's development standards, code style, testing practices, commit conventions, and quality gates. All contributors must follow these standards to ensure code quality and consistency.

For project overview, architecture, and business logic, see [PROJECT_SUMMARY.md](./PROJECT_SUMMARY.md).

## 1. Directory Structure

Key paths in the root directory:

- `dmr/`: Django project configuration (`settings.py`, `urls.py`, `asgi.py`, `wsgi.py`)
- `core/`: General permissions and authentication serializers
- `patients/`: Patient and file management
- `student_groups/`: Observation data and lab requests
- `instructors/`: Instructor-side management and statistics
- `tests/`: Centralized integration/end-to-end tests
- `docs/`: Project documentation
- `data/`: Contains database, media files, and static files (created automatically)
  - `data/media/`: User uploaded files
  - `data/static/`: Static files
  - `data/db.sqlite3`: SQLite database (default)

Suggested internal application structure (if new modules are needed):

- `admin.py`, `apps.py`, `models.py`, `serializers.py`, `views.py`, `urls.py`, `validators.py` (optional), `permissions.py` (try to centralize in `core`)
- `migrations/`: Submit migration files

## 2. Permission Development Guidelines

### 2.1 Architecture Principles

- **Centralized Location**: All general permission classes are located in `core/permissions.py`, uniformly inheriting `BaseRolePermission`.
- **RBAC Pattern**: Follow resource-based RBAC. Name permission classes after the resources they protect (e.g., `PatientPermission`, `InvestigationRequestPermission`), not after roles.
- **Method-Level Control**: Define allowed methods via `role_permissions` dict; admin defaults to full access when not explicitly restricted.
- **Object-Level Control**: Implement `has_object_permission` when needed (e.g., enforce `obj.user == request.user` for ownership checks).

### 2.2 Implementation Requirements

- **Explicit Declaration**: All views must explicitly set `permission_classes`; never rely on defaults.
- **Naming Convention**: `<ResourceName>Permission` (e.g., `PatientPermission`, `FileAccessPermission`).
- **Testing**: Every permission class must have tests covering all role scenarios (admin/instructor/student) and both positive and negative cases.

For detailed permission model and access control rules, see [PROJECT_SUMMARY.md](./PROJECT_SUMMARY.md#3-permission-model-and-access-control).

## 3. API Design and Serialization

- Use DRF ViewSet/GenericViewSet; list pagination uses `PageNumberPagination` (see `REST_FRAMEWORK` configuration).
- Schema: Use `drf-spectacular`; new/changed interfaces should be supplemented with `@extend_schema`, providing field descriptions and examples.
- Serializers: Common timestamp fields are provided by `core.serializers.BaseModelSerializer`; perform parameter/range validation in `validate()` to ensure business exceptions do not result in 500 errors.
- Consistency: Endpoint naming and URLName follow `<app>-<action>` (e.g., `patient-list`, `file-view`).

## 4. Data Models and Migrations

### 4.1 Model Development Standards

- **Field Documentation**: All model fields should have `verbose_name` and necessary `help_text`.
- **String Representation**: Implement `__str__` method for easier debugging and admin interface.
- **Naming**: Model class names in `PascalCase`; field names in `snake_case`.
- **Validation**: Override `clean()` method for model-level validation; raise `ValidationError` for business rule violations.

### 4.2 Migration Standards

- **Generation**: Always generate migration files for model changes using `python manage.py makemigrations`.
- **Review**: Review generated migrations before committing; ensure data compatibility.
- **Data Migrations**: Use data migrations for complex transformations; handle default values appropriately.
- **Commit**: Always commit migration files with the corresponding code changes.
- **Dependencies**: Be mindful of migration dependencies across apps.

## 5. Testing Standards

- Location:
  - Centralized directory `tests/`: Cross-app integration/end-to-end tests (e.g., login and overall workflows).
  - App internal: Unit tests are allowed (e.g., `patients/tests.py`, `instructors/tests.py`, etc.).
- Naming: `test_<feature>.py`; integration tests are `test_<feature>_integration.py`; test class names `<Feature>TestCase`/`<Feature>Test`.
- Tools: Use DRF `APIClient`; use `force_authenticate`, Token login, or Session when necessary.
- File-related tests: Use `override_settings(MEDIA_ROOT=tempfile.mkdtemp())`; clean up generated files after testing.
- Coverage Points:
  - Permissions: Positive and denial scenarios for admin/instructor/student.
  - Validation: Boundary and exception branches of `ObservationValidator`.
  - Transactions: All-or-nothing scenarios for `ObservationManager.create_observations`.
  - File Pagination: Denial of unauthorized page numbers and correct output for authorized page numbers.

## 6. Code Style and Tooling

- Formatting: Use `uv run ruff format .` to auto-format code.
- Linting: Use `uv run ruff check .` to check for code quality issues.
- Running commands: Use `uv run <command>` to run commands within the project's virtual environment (e.g., `uv run python manage.py runserver`).
- Managing dependencies: Use `uv pip install` or `uv sync` to install dependencies from `pyproject.toml`. Use `uv add <package>` to add new dependencies.
- Current Python version: 3.12+
- Current Django version: 5.2+
- Naming: Variables/functions `snake_case`; classes `PascalCase`; constants `UPPER_SNAKE_CASE`; private `_leading_underscore`.
- Structure: Smaller functions, clear responsibilities; extract common logic to utilities/base classes; avoid code duplication.
- Imports: Group by standard library, third-party, and project-internal; remove unused imports.
- Documentation: Provide Chinese docstrings for modules, classes, and methods; include examples when necessary.

## 7. Branches, Commits, and PRs

- Branches: `feature/<name>`, `fix/<name>`, `chore/<name>`.
- Commits: Recommend Conventional Commits (`feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`).
- PRs: Describe motivation, changes, verification methods, and scope of impact; link to issues; require at least one reviewer.

## 8. Development Workflow

1) Requirements Analysis: Clarify data relationships and permission boundaries; identify scope of impact.
2) Development: Adhere to existing style; minimize changes; declare permissions for new endpoints and supplement OpenAPI documentation; return 400 for input validation errors.
3) Testing: Accompany new features with unit and integration tests; cover positive and negative cases and boundaries; ensure regression passes.
4) Verification: Local run, basic smoke tests; review permissions, response formats, and documentation consistency.

## 9. Quality Gates

- Runnable: `runserver` without errors; key routes accessible.
- Lint/Type: No syntax/import errors; no obvious dead code; clean imports.
- Testing: Can run independently and pass locally; avoid external dependencies; use minimal datasets for slow tests.
- Documentation: Update relevant documentation and examples; Swagger synchronization.

## 10. Security and Compliance

- Authentication: Token and Session enabled by default; tighten CORS settings in production.
- Files: Only trusted sources can upload; strictly validate page ranges when enabling pagination authorization for PDFs; avoid exposing file system structure through paths.
- Data: Avoid real PII; example data is for teaching, note labeling.

## 11. Performance Best Practices

### 11.1 Database Queries

- **N+1 Prevention**: Always use `select_related()` for ForeignKey fields and `prefetch_related()` for ManyToMany relationships in `get_queryset()`.
- **Query Optimization**: Use `only()` and `defer()` to limit fields when appropriate.
- **Indexing**: Add database indexes for frequently queried fields (define in model's `Meta.indexes`).

### 11.2 API Performance

- **Pagination**: Enable pagination for all list endpoints; default pagination is configured in `REST_FRAMEWORK` settings.
- **Response Size**: Avoid returning large nested objects; use appropriate serializer depth.
- **Caching**: Consider caching for expensive queries (future extensibility).

## 12. Versioning and API Evolution

- **OpenAPI Schema**: `SCHEMA_PATH_PREFIX = "/api"` (configured in `SPECTACULAR_SETTINGS`).
- **API Versioning**: If versioning is introduced (e.g., `/api/v1`), routes, schema, documentation, and frontend must be updated synchronously.
- **Backward Compatibility**: Avoid breaking changes; deprecate features before removal.

## 13. Common Development Pitfalls

### 13.1 Permission Issues

- **Missing Declaration**: Forgetting to explicitly set `permission_classes` leads to default inheritance. Always declare explicitly.
- **Object-Level Checks**: Remember to implement `has_object_permission` for resource ownership validation.

### 13.2 Data Validation

- **Serializer Validation**: Always validate input in `validate()` method; return 400 errors for bad input, not 500.
- **Model Validation**: Implement `clean()` for model-level business rules.

### 13.3 File and Media

- **File Cleanup**: Override model's `delete()` method to remove files from disk.
- **Access Control**: Ensure file access is properly restricted by permissions and approved requests.

### 13.4 Testing

- **Isolation**: Use `override_settings(MEDIA_ROOT=tmpdir)` for file tests.
- **Cleanup**: Always clean up test data and files after tests.
- **External Dependencies**: Avoid real network calls or external services in tests.
