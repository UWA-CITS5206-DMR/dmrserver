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

    def __init__(self) -> None:
        super().__init__()
        self._role_cache: dict[str, str | None] = {}

    def has_permission(self, request: Request, _view: object) -> bool:
        """Check if user has permission to access the endpoint"""
        user_role = self._get_user_role(request.user)
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

    def _get_user_role(self, user: object | None) -> str | None:
        """
        Get user role with caching per username.

        Returns:
            str | None: User role or None if not authenticated or no role
        """
        if not user or not user.is_authenticated:
            return None

        username = user.username
        if username not in self._role_cache:
            self._role_cache[username] = get_user_role(user)

        return self._role_cache[username]

    def _check_ownership(self, request: Request, obj: object) -> bool:
        """
        Check if the user owns the object (for student role).
        Args:
            request: The HTTP request
            obj: The object being accessed
        Returns:
            bool: True if user owns the object, False otherwise
        """
        user_role = self._get_user_role(request.user)

        if user_role in (Role.ADMIN.value, Role.INSTRUCTOR.value):
            return True

        if user_role == Role.STUDENT.value:
            return hasattr(obj, "user") and obj.user == request.user

        return False


class StudentGroupPermission(BaseRolePermission):
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
        Role.INSTRUCTOR.value: SAFE_METHODS,  # Read-only access
    }

    def has_object_permission(
        self, request: Request, _view: object, obj: object
    ) -> bool:
        return self._check_ownership(request, obj)


class FileAccessPermission(BaseRolePermission):
    """
    Custom permission for file access with role-based and approval-based logic:
    - Admins and instructors: full access to all files
    - Students: can access files approved via lab requests or manual releases
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

    def has_object_permission(
        self, request: Request, _view: object, obj: object
    ) -> bool:
        """Check file access permissions"""
        user_role = self._get_user_role(request.user)

        if user_role in (Role.ADMIN.value, Role.INSTRUCTOR.value):
            return True

        # Students must have an approved investigation request or manual release
        if user_role == Role.STUDENT.value:
            # Check if file is approved in any completed investigation request
            imaging_request_exists = ApprovedFile.objects.filter(
                file=obj,
                imaging_request__user=request.user,
                imaging_request__status="completed",
            ).exists()
            blood_test_request_exists = ApprovedFile.objects.filter(
                file=obj,
                blood_test_request__user=request.user,
                blood_test_request__status="completed",
            ).exists()
            # Check if file has been manually released to the student
            manual_release_exists = ApprovedFile.objects.filter(
                file=obj,
                released_to_user=request.user,
            ).exists()

            return (
                imaging_request_exists
                or blood_test_request_exists
                or manual_release_exists
            )

        return False


class InvestigationRequestPermission(BaseRolePermission):
    """Unified permission for investigation request resources.

    Covers ImagingRequest, BloodTestRequest, MedicationOrder, and DischargeSummary APIs so
    instructors and students can share the same endpoints while keeping responsibilities clear.

    Access rules:
    - Students: can list, retrieve, create, and delete their own requests for their patients; updates remain blocked.
    - Instructors: full CRUD access to manage requests and approve results.
    - Admins: inherit full access (handled by BaseRolePermission).
    """

    role_permissions: ClassVar[dict[str, list[str] | tuple[str, ...]]] = {
        Role.STUDENT.value: [*SAFE_METHODS, "POST", "DELETE"],
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

    def has_object_permission(
        self, request: Request, _view: object, obj: object
    ) -> bool:
        return self._check_ownership(request, obj)


class GoogleFormLinkPermission(BaseRolePermission):
    """
    Permission for Google Form links access:
    - Students: read-only access to active forms
    - Instructors: full CRUD access to all forms
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


class MedicationOrderPermission(BaseRolePermission):
    """Permission for MedicationOrder resources.

    Access rules:
    - Students: can list, retrieve, create, update, and delete their own medication orders
    - Instructors: full CRUD access to manage medication orders
    - Admins: inherit full access (handled by BaseRolePermission)
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

    def has_object_permission(
        self, request: Request, _view: object, obj: object
    ) -> bool:
        return self._check_ownership(request, obj)


class DischargeSummaryPermission(BaseRolePermission):
    """Permission for DischargeSummary resources.

    Access rules:
    - Students: can list, retrieve, create, update, and delete their own discharge summaries
    - Instructors: full CRUD access to manage discharge summaries
    - Admins: inherit full access (handled by BaseRolePermission)
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

    def has_object_permission(
        self, request: Request, _view: object, obj: object
    ) -> bool:
        return self._check_ownership(request, obj)
