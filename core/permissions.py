"""
Role-based access control (RBAC) permissions for DMR server.

This module defines permissions based on user roles:
- admin: Full access to all resources and operations
- instructor: Can modify patient data and files, approve lab requests, read all observations
- student: Can create/modify their own observations and notes, read patient data (view-only), create lab requests
"""

from rest_framework.permissions import BasePermission, SAFE_METHODS


# Role constants
ROLE_ADMIN = "admin"
ROLE_INSTRUCTOR = "instructor"
ROLE_STUDENT = "student"


def get_user_role(user):
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
    if user.is_superuser or user.groups.filter(name=ROLE_ADMIN).exists():
        return ROLE_ADMIN

    # Check for instructor role
    if user.groups.filter(name=ROLE_INSTRUCTOR).exists():
        return ROLE_INSTRUCTOR

    # Check for student role
    if user.groups.filter(name=ROLE_STUDENT).exists():
        return ROLE_STUDENT

    return None


class BaseRolePermission(BasePermission):
    """
    Base permission class that handles common role checking logic.
    Subclasses should override role_permissions dict and optionally has_object_permission.
    """

    # Override in subclasses: {role: [allowed_methods]}
    role_permissions = {}

    def has_permission(self, request, view):
        """Check if user has permission to access the endpoint"""
        if not request.user.is_authenticated:
            return False

        user_role = get_user_role(request.user)
        if not user_role:
            return False

        # Admin always has full access unless explicitly restricted
        if user_role == ROLE_ADMIN and ROLE_ADMIN not in self.role_permissions:
            return True

        allowed_methods = self.role_permissions.get(user_role, [])
        return request.method in allowed_methods

    def has_object_permission(self, request, view, obj):
        """Default object permission - same as has_permission"""
        return self.has_permission(request, view)


class PatientPermission(BaseRolePermission):
    """
    Permission for patient data access:
    - Students: read-only access
    - Instructors: full CRUD access
    - Admin: full access (inherited)
    """

    role_permissions = {
        ROLE_STUDENT: SAFE_METHODS,
        ROLE_INSTRUCTOR: ["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"],
    }


class ObservationPermission(BaseRolePermission):
    """
    Permission for observation data (notes, blood pressure, etc.):
    - Students: full CRUD access to their own observations
    - Instructors: read-only access to all observations
    - Admin: full access (inherited)
    """

    role_permissions = {
        ROLE_STUDENT: ["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"],
        ROLE_INSTRUCTOR: SAFE_METHODS,
    }

    def has_object_permission(self, request, view, obj):
        """Students can only access their own observations"""
        if not request.user.is_authenticated:
            return False

        user_role = get_user_role(request.user)
        if not user_role:
            return False

        # Admin has full access
        if user_role == ROLE_ADMIN:
            return True

        # Instructor has read-only access to all observations
        if user_role == ROLE_INSTRUCTOR:
            return request.method in SAFE_METHODS

        # Student can only access their own observations
        if user_role == ROLE_STUDENT:
            return hasattr(obj, "user") and obj.user == request.user

        return False


class LabRequestPermission(BaseRolePermission):
    """
    Permission for student lab request operations in student_groups app:
    - Students: can create and read their own lab requests
    - Instructors: read-only access (full CRUD handled in instructor app)
    - Admin: full access (inherited)
    """

    role_permissions = {
        ROLE_STUDENT: ["GET", "POST", "HEAD", "OPTIONS"],
        ROLE_INSTRUCTOR: SAFE_METHODS,
    }

    def has_object_permission(self, request, view, obj):
        """Students can only access their own requests, instructors have read-only access"""
        if not request.user.is_authenticated:
            return False

        user_role = get_user_role(request.user)
        if not user_role:
            return False

        # Admin has full access
        if user_role == ROLE_ADMIN:
            return True

        # Instructor has read-only access to all lab requests
        if user_role == ROLE_INSTRUCTOR:
            return request.method in SAFE_METHODS

        # Student can only access their own lab requests (read-only after creation)
        if user_role == ROLE_STUDENT:
            return (
                hasattr(obj, "user")
                and obj.user == request.user
                and request.method in SAFE_METHODS
            )

        return False


class InstructorOnlyPermission(BaseRolePermission):
    """
    Permission that allows access only to instructors and admins.
    Used for instructor-specific endpoints and dashboards.
    """

    role_permissions = {
        ROLE_INSTRUCTOR: ["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"],
    }
