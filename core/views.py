from typing import ClassVar

from django.db import DatabaseError
from drf_spectacular.utils import OpenApiExample, extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from .models import MultiDeviceToken
from .serializers import AuthTokenSerializer, LoginSerializer, UserSerializer


class AuthViewSet(viewsets.GenericViewSet):
    """
    Authentication ViewSet for user login, logout and profile management
    """

    permission_classes: ClassVar[list] = [AllowAny]

    @extend_schema(
        summary="User login",
        description="Authenticate user and return access token",
        request=LoginSerializer,
        responses={200: AuthTokenSerializer},
        examples=[
            OpenApiExample(
                "Login Request",
                value={"username": "student1", "password": "password123"},
            ),
        ],
    )
    @action(detail=False, methods=["post"], permission_classes=[AllowAny])
    def login(self, request: Request) -> Response:
        """Login user and return token with user information.

        Creates a new token for each login, allowing multiple devices to be logged in simultaneously.
        """
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data["user"]
        # Create a new token for each login to support multi-device access
        token = MultiDeviceToken.objects.create(user=user)

        response_data = {"token": token.key, "user": UserSerializer(user).data}

        return Response(response_data, status=status.HTTP_200_OK)

    @extend_schema(
        summary="User logout",
        description="Logout user by invalidating the current token",
        responses={200: {"description": "Successfully logged out"}},
    )
    @action(detail=False, methods=["post"], permission_classes=[IsAuthenticated])
    def logout(self, request: Request) -> Response:
        """Logout user by deleting the current device token.

        Only deletes the token used in this request, allowing other devices to remain logged in.
        """
        # Delete only the current token (from request.auth), not all user tokens
        if request.auth:
            try:
                request.auth.delete()
            except (AttributeError, DatabaseError) as exc:
                return Response(
                    {"detail": f"Logout failed: {exc!s}"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            return Response(
                {"detail": "Successfully logged out"},
                status=status.HTTP_200_OK,
            )

        return Response(
            {"detail": "No active token found"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    @extend_schema(
        summary="Get user profile",
        description="Retrieve current authenticated user's profile information",
        responses={200: UserSerializer},
    )
    @action(detail=False, methods=["get"], permission_classes=[IsAuthenticated])
    def profile(self, request: Request) -> Response:
        """Get current user profile with role information"""
        serializer = UserSerializer(request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)
