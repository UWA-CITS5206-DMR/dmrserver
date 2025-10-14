"""Role-based access control (RBAC) permissions for DMR server.

This module defines permissions based on user roles:
- admin: Full access to all resources and operations
- instructor: Can modify patient data and files, approve lab requests, read all observations
- student: Can create/modify their own observations and notes, read patient data (view-only), create lab requests
"""

from typing import ClassVar

from rest_framework.permissions import SAFE_METHODS, BasePermission
from rest_framework.request import Request

from student_groups.models import ApprovedFile

from .context import Role


def get_user_role(user: object | None) -> str | None:
    """
    Get the primary role of a user based on group membership.

    Returns the highest privilege role if user belongs to multiple groups.
    Hierarchy: admin > instructor > student

    Args:
        user: Django User instance

    Returns:
        str: Role name or None if user has no recognized role
    """
    if not user or not user.is_authenticated:
        return None

    # Check for admin role (superuser or admin group)
    if user.is_superuser or user.groups.filter(name=Role.ADMIN.value).exists():
        return Role.ADMIN.value

    # Check for instructor role
    if user.groups.filter(name=Role.INSTRUCTOR.value).exists():
        return Role.INSTRUCTOR.value

    # Check for student role
    if user.groups.filter(name=Role.STUDENT.value).exists():
        return Role.STUDENT.value

    return None


class BaseRolePermission(BasePermission):
    """
    Base permission class that handles common role checking logic.
    Subclasses should override role_permissions dict and optionally has_object_permission.
    """

    # Override in subclasses: {role: [allowed_methods]}
    role_permissions: ClassVar[dict[str, list[str] | tuple[str, ...]]] = {}

    def has_permission(self, request: Request, _view: object) -> bool:
        """Check if user has permission to access the endpoint"""
        if not request.user.is_authenticated:
            return False

        user_role = get_user_role(request.user)
        if not user_role:
            return False

        # Admin always has full access unless explicitly restricted
        if (
            user_role == Role.ADMIN.value
            and Role.ADMIN.value not in self.role_permissions
        ):
            return True

        allowed_methods = self.role_permissions.get(user_role, [])
        return request.method in allowed_methods

    def has_object_permission(
        self, request: Request, _view: object, _obj: object
    ) -> bool:
        """Default object permission - same as has_permission"""
        return self.has_permission(request, _view)


class InstructorManagementPermission(BaseRolePermission):
    """
    Permission for instructor management endpoints (dashboard, request management).

    This permission protects instructor-side endpoints that provide full CRUD
    access to lab requests and dashboard statistics.

    Access rules:
    - Instructors: full CRUD access to all management functions
    - Admins: full access (inherited)
    - Students: no access

    Use this for:
    - Instructor dashboard endpoints
    - Instructor-side lab request management
    - Any instructor-specific management features
    """

    role_permissions: ClassVar[dict[str, list[str] | tuple[str, ...]]] = {
        Role.INSTRUCTOR.value: [
            "GET",
            "POST",
            "PUT",
            "PATCH",
            "DELETE",
            "HEAD",
            "OPTIONS",
        ],
    }


class PatientPermission(BaseRolePermission):
    """
    Permission for patient data access:
    - Students: read-only access
    - Instructors: full CRUD access
    - Admin: full access (inherited)
    """

    role_permissions: ClassVar[dict[str, list[str] | tuple[str, ...]]] = {
        Role.STUDENT.value: SAFE_METHODS,
        Role.INSTRUCTOR.value: [
            "GET",
            "POST",
            "PUT",
            "PATCH",
            "DELETE",
            "HEAD",
            "OPTIONS",
        ],
    }


class ObservationPermission(BaseRolePermission):
    """
    Permission for observation data (notes, blood pressure, etc.):
    - Students: full CRUD access to their own observations
    - Instructors: read-only access to all observations
    - Admin: full access (inherited)
    """

    role_permissions: ClassVar[dict[str, list[str] | tuple[str, ...]]] = {
        Role.STUDENT.value: [
            "GET",
            "POST",
            "PUT",
            "PATCH",
            "DELETE",
            "HEAD",
            "OPTIONS",
        ],
        Role.INSTRUCTOR.value: SAFE_METHODS,
    }

    def has_object_permission(
        self, request: Request, _view: object, obj: object
    ) -> bool:
        """Students can only access their own observations"""
        if not request.user.is_authenticated:
            return False

        user_role = get_user_role(request.user)
        if not user_role:
            return False

        # Admin has full access
        if user_role == Role.ADMIN.value:
            return True

        # Instructor has read-only access to all observations
        if user_role == Role.INSTRUCTOR.value:
            return request.method in SAFE_METHODS

        # Student can only access their own observations
        if user_role == Role.STUDENT.value:
            return hasattr(obj, "user") and obj.user == request.user

        return False


class FileAccessPermission(BaseRolePermission):
    """
    Custom permission for file access with role-based and approval-based logic:
    - Admins and instructors: full access to all files
    - Students: can access files approved via lab requests or manual releases
    """

    role_permissions: ClassVar[dict[str, list[str] | tuple[str, ...]]] = {
        Role.STUDENT.value: SAFE_METHODS,
        Role.INSTRUCTOR.value: SAFE_METHODS,
    }

    def has_object_permission(
        self, request: Request, _view: object, obj: object
    ) -> bool:
        """Check file access permissions"""
        user = request.user

        if not user.is_authenticated:
            return False

        user_role = get_user_role(user)
        if not user_role:
            return False

        # Admins and instructors have full access
        if user_role in [Role.ADMIN.value, Role.INSTRUCTOR.value]:
            return True

        # Students must have an approved lab request for this file
        if user_role == Role.STUDENT.value:
            # Check if file is approved in any completed lab request for this student
            imaging_request_exists = ApprovedFile.objects.filter(
                file=obj,
                imaging_request__user=user,
                imaging_request__status="completed",
            ).exists()

            blood_test_request_exists = ApprovedFile.objects.filter(
                file=obj,
                blood_test_request__user=user,
                blood_test_request__status="completed",
            ).exists()

            manual_release_exists = ApprovedFile.objects.filter(
                file=obj,
                released_to_user=user,
            ).exists()

            return (
                imaging_request_exists
                or blood_test_request_exists
                or manual_release_exists
            )

        return False


class FileManagementPermission(BaseRolePermission):
    """
    Permission for file management (CRUD operations on files).
    Only instructors and admins can manage files.
    """

    role_permissions: ClassVar[dict[str, list[str] | tuple[str, ...]]] = {
        Role.INSTRUCTOR.value: [
            "GET",
            "POST",
            "PUT",
            "PATCH",
            "DELETE",
            "HEAD",
            "OPTIONS",
        ],
    }


class FileListPermission(BaseRolePermission):
    """
    Permission for listing patient files.

    This permission allows students to view file lists (read-only),
    while instructors and admins have full access.

    Access rules:
    - Students: read-only access to file lists (actual files shown are filtered by queryset)
    - Instructors: full access to all file lists
    - Admins: full access (inherited)

    Note: The queryset filtering is handled in the view layer to show:
    - Students: Only Admission files + approved files from completed requests
    - Instructors/Admins: All files
    """

    role_permissions: ClassVar[dict[str, list[str] | tuple[str, ...]]] = {
        Role.STUDENT.value: SAFE_METHODS,
        Role.INSTRUCTOR.value: [
            "GET",
            "POST",
            "PUT",
            "PATCH",
            "DELETE",
            "HEAD",
            "OPTIONS",
        ],
    }


class LabRequestPermission(BaseRolePermission):
    """
    Permission for lab request resources (ImagingRequest, BloodTestRequest,
    MedicationOrder, DischargeSummary).

    This permission provides unified access control for all lab request types,
    ensuring consistent RBAC enforcement across student-side endpoints.

    Access rules:
    - Students: can create and view their own requests (object-level check)
    - Instructors: no access (use InstructorManagementPermission for instructor-side endpoints)
    - Admins: full access to all operations

    Note: This permission is designed for student-side lab request endpoints.
    Instructor-side endpoints should use InstructorManagementPermission.
    """

    role_permissions: ClassVar[dict[str, list[str] | tuple[str, ...]]] = {
        Role.STUDENT.value: [
            "GET",
            "POST",
            "HEAD",
            "OPTIONS",
        ],
    }

    def has_object_permission(
        self, request: Request, _view: object, obj: object
    ) -> bool:
        """
        Check object-level permissions for lab requests.
        Students can only access their own requests.
        """
        if not request.user.is_authenticated:
            return False

        user_role = get_user_role(request.user)
        if not user_role:
            return False

        # Admin has full access
        if user_role == Role.ADMIN.value:
            return True

        # Students can only access their own requests
        if user_role == Role.STUDENT.value:
            return hasattr(obj, "user") and obj.user == request.user

        return False
