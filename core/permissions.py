"""
Role-based access control (RBAC) permissions for DMR server.

This module defines permissions based on user roles:
- admin: Full access to all resources and operations
- instructor: Can read all data, can update LabRequest status from pending to completed
- student: Can only create LabRequests, can read patient data (view-only)
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


class LabRequestPermission(BasePermission):
    """
    Permission class for LabRequest operations based on user roles.

    Permission rules:
    - admin: Full CRUD access
    - instructor: Can create, read, and update status field only
    - student: Can only create requests
    """

    def has_permission(self, request, view):
        """Check if user has permission to access the endpoint"""
        if not request.user.is_authenticated:
            return False

        user_role = get_user_role(request.user)
        if not user_role:
            return False

        # Admin has full access
        if user_role == ROLE_ADMIN:
            return True

        # Student can only create (POST)
        if user_role == ROLE_STUDENT:
            return request.method == "POST"

        # Instructor can create, read, and update
        if user_role == ROLE_INSTRUCTOR:
            return request.method in ["POST", "GET", "HEAD", "OPTIONS", "PATCH", "PUT"]

        return False

    def has_object_permission(self, request, view, obj):
        """Check if user has permission to access specific object"""
        if not request.user.is_authenticated:
            return False

        user_role = get_user_role(request.user)
        if not user_role:
            return False

        # Admin has full access
        if user_role == ROLE_ADMIN:
            return True

        # Student cannot access existing objects (per requirements)
        if user_role == ROLE_STUDENT:
            return False

        # Instructor can read and update (with field restrictions handled in serializer)
        if user_role == ROLE_INSTRUCTOR:
            return request.method in SAFE_METHODS or request.method in ["PATCH", "PUT"]

        return False


class IsAdminOrReadOnly(BasePermission):
    """
    Permission class that allows read access to authenticated users
    but write access only to admin users.

    Useful for Patient model where students need read access
    but only admins should modify patient data.
    """

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False

        # Read permissions for any authenticated user
        if request.method in SAFE_METHODS:
            return True

        # Write permissions only for admin
        user_role = get_user_role(request.user)
        return user_role == ROLE_ADMIN
