from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from .permissions import get_user_role


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(style={"input_type": "password"})

    def validate(self, attrs):
        username = attrs.get("username")
        password = attrs.get("password")

        if username and password:
            user = authenticate(username=username, password=password)
            if not user:
                raise serializers.ValidationError("Invalid credentials")
            if not user.is_active:
                raise serializers.ValidationError("User account is disabled")
            attrs["user"] = user
            return attrs
        else:
            raise serializers.ValidationError("Must include username and password")


class UserSerializer(serializers.ModelSerializer):
    role = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "is_staff",
            "is_superuser",
            "role",
        ]
        read_only_fields = ["id", "is_staff", "is_superuser", "role"]

    def get_role(self, obj):
        """Get user role using the project's role system"""
        return get_user_role(obj)


class AuthTokenSerializer(serializers.Serializer):
    token = serializers.CharField()
    user = UserSerializer(read_only=True)
