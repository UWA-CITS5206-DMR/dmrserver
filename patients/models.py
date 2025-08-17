import os
import glob
import uuid
from datetime import datetime
from django.conf import settings
from django.db import models


class Patient(models.Model):
    first_name = models.CharField(max_length=100, verbose_name="First Name")
    last_name = models.CharField(max_length=100, verbose_name="Last Name")
    date_of_birth = models.DateField(verbose_name="Date of Birth")
    email = models.EmailField(unique=True, verbose_name="Email Address")
    phone_number = models.CharField(
        max_length=15, blank=True, verbose_name="Phone Number"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created At")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Updated At")

    class Meta:
        verbose_name = "Patient"
        verbose_name_plural = "Patients"
        ordering = ["last_name", "first_name"]

    def __str__(self):
        return f"{self.first_name} {self.last_name}"


class File(models.Model):
    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False, verbose_name="File ID"
    )
    display_name = models.CharField(
        max_length=255, editable=False, verbose_name="Display name"
    )
    file = models.FileField(upload_to="upload_to", verbose_name="File")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created At")

    class Meta:
        verbose_name = "File"
        verbose_name_plural = "Files"

    @staticmethod
    def upload_to(instance, filename):
        today = datetime.today().strftime("%Y/%m/%d")
        ext = filename.split(".")[-1]
        unique_filename = f"{instance.id}.{ext}"
        return os.path.join("uploads", today, unique_filename)

    def get_full_path(self):
        return os.path.join(settings.MEDIA_ROOT, self.file.path)

    def delete(self, *args, **kwargs):
        files = glob.glob(f"{self.get_full_path()}*")
        for file in files:
            os.remove(file)
        self.file.delete(save=False)
        super().delete(*args, **kwargs)

    def __str__(self):
        return self.display_name or str(self.id)
