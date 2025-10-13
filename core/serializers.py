from typing import ClassVar

from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from rest_framework import serializers

from .permissions import get_user_role


class BaseModelSerializer(serializers.ModelSerializer):
    """
    Base serializer with common timestamp fields for all models.
    Centralizes the handling of created_at and updated_at fields.
    """

    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(style={"input_type": "password"})

    def validate(self, attrs: dict) -> dict:
        username = attrs.get("username")
        password = attrs.get("password")

        if username and password:
            user = authenticate(username=username, password=password)
            if not user:
                msg = "Invalid credentials"
                raise serializers.ValidationError(msg)
            if not user.is_active:
                msg = "User account is disabled"
                raise serializers.ValidationError(msg)
            attrs["user"] = user
            return attrs
        msg = "Must include username and password"
        raise serializers.ValidationError(msg)


class UserSerializer(serializers.ModelSerializer):
    role = serializers.SerializerMethodField()

    class Meta:
        model = User

    fields: ClassVar[list[str]] = [
        "id",
        "username",
        "email",
        "first_name",
        "last_name",
        "is_staff",
        "is_superuser",
        "role",
    ]
    read_only_fields: ClassVar[list[str]] = ["id", "is_staff", "is_superuser", "role"]

    def get_role(self, obj: User) -> str | None:
        """Get user role using the project's role system"""
        return get_user_role(obj)


class AuthTokenSerializer(serializers.Serializer):
    token = serializers.CharField()
    user = UserSerializer(read_only=True)
