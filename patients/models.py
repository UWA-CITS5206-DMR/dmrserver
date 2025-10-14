import uuid
from pathlib import Path
from typing import ClassVar

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class Patient(models.Model):
    class Gender(models.TextChoices):
        FEMALE = "female", "Female"
        MALE = "male", "Male"
        OTHER = "other", "Other"
        UNSPECIFIED = "unspecified", "Unspecified"

    first_name = models.CharField(max_length=100, verbose_name="First Name")
    last_name = models.CharField(max_length=100, verbose_name="Last Name")
    date_of_birth = models.DateField(verbose_name="Date of Birth")
    gender = models.CharField(
        max_length=20,
        choices=Gender.choices,
        default=Gender.UNSPECIFIED,
        verbose_name="Gender",
        help_text="Patient's gender",
    )
    mrn = models.CharField(
        max_length=50,
        unique=True,
        verbose_name="Medical Record Number (MRN)",
    )
    ward = models.CharField(max_length=100, verbose_name="Ward")
    bed = models.CharField(max_length=20, verbose_name="Bed")
    phone_number = models.CharField(
        max_length=15,
        blank=True,
        verbose_name="Phone Number",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created At")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Updated At")

    class Meta:
        verbose_name = "Patient"
        verbose_name_plural = "Patients"
        ordering: ClassVar[list[str]] = ["last_name", "first_name"]

    def __str__(self) -> str:
        return f"{self.first_name} {self.last_name}"


def validate_pdf_for_pagination(
    *, file: object | None = None, requires_pagination: bool = False
) -> None:
    # Only validate when a file is present and pagination is requested
    if not requires_pagination:
        return
    if not file:
        # No file provided, nothing to validate here (other validators can enforce presence)
        return

    ext = Path(getattr(file, "name", "")).suffix
    if ext.lower() != ".pdf":
        msg = "Only PDF files can be marked for pagination."
        raise ValidationError(msg)


class File(models.Model):
    class Category(models.TextChoices):
        ADMISSION = "Admission", "Admission"
        PATHOLOGY = "Pathology", "Pathology"
        IMAGING = "Imaging", "Imaging"
        DIAGNOSTICS = "Diagnostics", "Diagnostics"
        LAB_RESULTS = "Lab Results", "Lab Results"
        OTHER = "Other", "Other"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name="File ID",
    )
    patient = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE,
        related_name="files",
        verbose_name="Patient",
    )
    display_name = models.CharField(
        max_length=255,
        editable=False,
        verbose_name="Display name",
    )
    category = models.CharField(
        max_length=20,
        choices=Category.choices,
        default=Category.OTHER,
        verbose_name="Category",
    )
    file = models.FileField(upload_to="upload_to", verbose_name="File")
    requires_pagination = models.BooleanField(
        default=False,
        verbose_name="Requires Pagination",
        help_text="Only for PDF files. If true, access can be granted by page ranges.",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created At")

    class Meta:
        verbose_name = "File"
        verbose_name_plural = "Files"
        ordering: ClassVar[list[str]] = ["-created_at"]

    def __str__(self) -> str:
        return self.display_name or str(self.id)

    def save(self, *args: object, **kwargs: object) -> None:
        """
        Override save method to automatically set display_name.
        If display_name is not set and file is uploaded, extract filename.
        """
        if not self.display_name and self.file:
            # Extract original filename from file path
            self.display_name = Path(self.file.name).name
        super().save(*args, **kwargs)

    def clean(self) -> None:
        super().clean()
        validate_pdf_for_pagination(
            file=self.file, requires_pagination=self.requires_pagination
        )

    @staticmethod
    def upload_to(instance: object, filename: str) -> str:
        today = timezone.now().strftime("%Y/%m/%d")
        ext = filename.split(".")[-1]
        # Ensure we always have an identifier to use (instance.id may be None in some cases)
        file_id = getattr(instance, "id", None) or uuid.uuid4()
        unique_filename = f"{file_id}.{ext}"
        return str(Path("uploads") / today / unique_filename)

    def get_full_path(self) -> str | None:
        # self.file.path is already an absolute filesystem path when using
        # the default FileSystemStorage. Return it directly for correctness.
        return getattr(self.file, "path", None)

    def delete(self, *args: object, **kwargs: object) -> None:
        self.file.delete(save=False)
        super().delete(*args, **kwargs)


class GoogleFormLink(models.Model):
    """
    Model for storing Google Form links that are displayed to all patients.
    These forms are global and not patient-specific.
    """

    title = models.CharField(
        max_length=255,
        verbose_name="Form Title",
        help_text="The title of the Google Form",
    )
    url = models.URLField(
        max_length=500,
        verbose_name="Form URL",
        help_text="The complete URL to the Google Form",
    )
    description = models.TextField(
        blank=True,
        verbose_name="Description",
        help_text="Optional description of the form's purpose",
    )
    display_order = models.IntegerField(
        default=0,
        verbose_name="Display Order",
        help_text="Order in which the form appears (lower numbers first)",
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Is Active",
        help_text="Whether this form link is currently active and visible",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created At")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Updated At")

    class Meta:
        verbose_name = "Google Form Link"
        verbose_name_plural = "Google Form Links"
        ordering: ClassVar[list[str]] = ["display_order", "created_at"]

    def __str__(self) -> str:
        return self.title
