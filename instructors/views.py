from typing import Any, ClassVar

from django.contrib.auth.models import User
from django.db.models import QuerySet
from rest_framework import viewsets

from core.context import Role
from core.permissions import StudentGroupPermission
from core.serializers import UserSerializer


class StudentGroupViewSet(viewsets.ReadOnlyModelViewSet):
    """Expose student group accounts to instructors for manual file releases."""

    permission_classes: ClassVar[list[Any]] = [StudentGroupPermission]
    serializer_class = UserSerializer
    pagination_class = None

    def get_queryset(self) -> QuerySet:
        return (
            User.objects.filter(groups__name=Role.STUDENT.value)
            .order_by("username")
            .distinct()
        )
