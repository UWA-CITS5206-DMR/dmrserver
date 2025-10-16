from typing import Any, ClassVar

from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.core.exceptions import FieldDoesNotExist
from rest_framework import serializers

from .permissions import get_user_role


class BaseModelSerializer(serializers.ModelSerializer):
    """
    Base serializer with common timestamp fields for all models.
    Centralizes the handling of created_at and updated_at fields.
    Automatically sets the user field from the request context if available.
    """

    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)

    def create(self, validated_data: dict[str, Any]) -> object:
        # Automatically set user from request context if the model has a user field
        # and it's not already provided in validated_data
        request = self.context.get("request")
        if (
            request
            and request.user.is_authenticated
            and "user" not in validated_data
            and hasattr(self.Meta.model, "_meta")
        ):
            try:
                self.Meta.model._meta.get_field("user")  # noqa: SLF001
                validated_data["user"] = request.user
            except FieldDoesNotExist:
                # Field doesn't exist, skip
                pass
        return super().create(validated_data)


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
        read_only_fields: ClassVar[list[str]] = [
            "id",
            "is_staff",
            "is_superuser",
            "role",
        ]

    def get_role(self, obj: User) -> str | None:
        """Get user role using the project's role system"""
        return get_user_role(obj)


class AuthTokenSerializer(serializers.Serializer):
    token = serializers.CharField()
    user = UserSerializer(read_only=True)
