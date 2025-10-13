import binascii
import os

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class MultiDeviceToken(models.Model):
    """
    Token model that supports multiple tokens per user for multi-device login.
    Each token represents a separate device/session.
    """

    key = models.CharField(_("Key"), max_length=40, primary_key=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="auth_tokens",
        on_delete=models.CASCADE,
        verbose_name=_("User"),
    )
    created = models.DateTimeField(_("Created"), auto_now_add=True)

    class Meta:
        verbose_name = _("Token")
        verbose_name_plural = _("Tokens")

    def __str__(self) -> str:
        return self.key

    def save(self, *args: object, **kwargs: object) -> None:
        if not self.key:
            self.key = self.generate_key()
        return super().save(*args, **kwargs)

    @classmethod
    def generate_key(cls) -> str:
        return binascii.hexlify(os.urandom(20)).decode()
