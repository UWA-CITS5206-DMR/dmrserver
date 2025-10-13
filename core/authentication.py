from rest_framework import exceptions
from rest_framework.authentication import TokenAuthentication as BaseTokenAuthentication
from .models import MultiDeviceToken


class MultiDeviceTokenAuthentication(BaseTokenAuthentication):
    """
    Token authentication that supports multiple tokens per user.
    Each token represents a separate device/session.
    """

    model = MultiDeviceToken

    def authenticate_credentials(self, key):
        try:
            token = self.model.objects.select_related("user").get(key=key)
        except self.model.DoesNotExist:
            raise exceptions.AuthenticationFailed("Invalid token.")

        if not token.user.is_active:
            raise exceptions.AuthenticationFailed("User inactive or deleted.")

        return (token.user, token)
