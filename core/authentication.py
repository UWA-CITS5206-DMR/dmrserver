from typing import Any

from rest_framework import exceptions
from rest_framework.authentication import TokenAuthentication as BaseTokenAuthentication

from .models import MultiDeviceToken


class MultiDeviceTokenAuthentication(BaseTokenAuthentication):
    """
    Token authentication that supports multiple tokens per user.
    Each token represents a separate device/session.
    """

    model = MultiDeviceToken

    def authenticate_credentials(self, key: str) -> tuple[Any, Any]:
        try:
            token = self.model.objects.select_related("user").get(key=key)
        except self.model.DoesNotExist:
            msg = "Invalid token."
            # Raise from None to avoid masking unexpected errors (B904)
            raise exceptions.AuthenticationFailed(msg) from None

        if not token.user.is_active:
            msg = "User inactive or deleted."
            raise exceptions.AuthenticationFailed(msg) from None

        return (token.user, token)
