from pathlib import Path
from typing import ClassVar

from django.contrib.auth.models import User
from rest_framework import serializers

from core.context import Role
from core.serializers import UserSerializer
from patients.services.pdf_pagination import PdfPageRangeParser
from student_groups.models import ApprovedFile

from .models import File, GoogleFormLink, Patient


class FileSerializer(serializers.ModelSerializer):
    """
    Serializer for File model.

    Handles file uploads with validation for:
    - Category selection
    - PDF pagination requirement (only PDFs can have requires_pagination=True)
    - Automatic display_name generation from uploaded filename
    """

    file = serializers.FileField(
        max_length=None,
        use_url=True,
        help_text="The file to upload. Supported formats depend on use case.",
    )
    requires_pagination = serializers.BooleanField(
        default=False,
        help_text="Set to true for PDF files that should use page-based authorization. Only valid for PDF files.",
    )

    class Meta:
        model = File
        fields: ClassVar[list[str]] = [
            "id",
            "patient",
            "display_name",
            "category",
            "file",
            "requires_pagination",
            "created_at",
        ]
        read_only_fields: ClassVar[list[str]] = [
            "id",
            "patient",
            "display_name",
            "created_at",
        ]

    def validate(self, attrs: dict) -> dict:
        """
        Validate that requires_pagination can only be True for PDF files.
        This validation runs before model.clean() to provide clear API error messages.
        """
        file_obj = attrs.get("file")
        requires_pagination = attrs.get("requires_pagination", False)

        if requires_pagination and file_obj:
            filename = getattr(file_obj, "name", "")
            ext = Path(filename).suffix.lower()
            if ext != ".pdf":
                raise serializers.ValidationError(
                    {
                        "requires_pagination": "Only PDF files can be marked for pagination. Current file type: {}".format(
                            ext or "unknown",
                        ),
                    },
                )

        return attrs

    def create(self, validated_data: dict) -> File:
        """
        Create a new File instance.

        Automatically sets:
        - display_name from the uploaded file's name
        - patient_id from the ViewSet context (for nested routes)

        This allows CacheMixin in the ViewSet to automatically handle
        cache invalidation without overriding perform_create.
        """
        validated_data["display_name"] = validated_data["file"].name

        # Set patient from view kwargs if available (supports nested routes)
        view = self.context.get("view")
        if view and hasattr(view, "kwargs"):
            patient_pk = view.kwargs.get("patient_pk")
            if patient_pk:
                validated_data["patient_id"] = patient_pk

        return super().create(validated_data)


class ManualFileReleaseSerializer(serializers.Serializer):
    """Serializer for manually releasing a file to one or more student groups."""

    student_group_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        allow_empty=False,
        help_text="IDs of student group user accounts to receive file access.",
    )
    page_range = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Page range to expose when the file requires pagination (e.g. '1-3,5').",
    )

    def validate_student_group_ids(self, value: list[int]) -> list[int]:
        """Ensure at least one unique student group id is provided."""
        unique_ids = list(dict.fromkeys(value))
        if not unique_ids:
            msg = "At least one student group must be selected."
            raise serializers.ValidationError(msg)
        return unique_ids

    def validate(self, attrs: dict) -> dict:
        file_instance: File = self.context["file"]
        ids: list[int] = attrs["student_group_ids"]

        students = list(
            User.objects.filter(id__in=ids, groups__name=Role.STUDENT.value).distinct()
        )
        found_ids = {user.id for user in students}
        missing = sorted(set(ids) - found_ids)
        if missing:
            msg = f"Invalid student group IDs: {', '.join(map(str, missing))}."
            raise serializers.ValidationError({"student_group_ids": msg})

        attrs["students"] = students

        page_range = attrs.get("page_range", "").strip()

        if file_instance.requires_pagination:
            if not page_range:
                msg = "Page range is required for files that enforce pagination."
                raise serializers.ValidationError({"page_range": msg})
            try:
                PdfPageRangeParser.parse(page_range)
            except (
                ValueError
            ) as exc:  # pragma: no cover - ValueError raised by int conversion
                msg = "Invalid page range format. Use values such as '1-3,5'."
                raise serializers.ValidationError({"page_range": msg}) from exc
            attrs["page_range"] = page_range
        else:
            if page_range:
                msg = "Page range should only be provided for paginated files."
                raise serializers.ValidationError({"page_range": msg})
            attrs["page_range"] = ""

        return attrs

    def save(self, *, released_by: User) -> list[ApprovedFile]:
        file_instance: File = self.context["file"]
        students: list[User] = self.validated_data["students"]
        page_range: str = self.validated_data.get("page_range", "")

        approved_files: list[ApprovedFile] = []
        for student in students:
            approved_file, _created = ApprovedFile.objects.update_or_create(
                file=file_instance,
                released_to_user=student,
                defaults={
                    "page_range": page_range,
                    "released_by": released_by,
                    "imaging_request": None,
                    "blood_test_request": None,
                },
            )
            approved_files.append(approved_file)

        return approved_files


class ManualFileReleaseResponseSerializer(serializers.Serializer):
    file_id = serializers.UUIDField()
    page_range = serializers.CharField(allow_blank=True)
    released_to = UserSerializer(many=True, read_only=True)


class PatientSerializer(serializers.ModelSerializer):
    """
    Serializer for Patient model.

    Files are managed separately through the File API endpoints.
    Students access files through approved_files in completed lab requests.
    Instructors access files through the dedicated File management endpoints.
    """

    gender = serializers.ChoiceField(
        choices=Patient.Gender.choices,
        required=False,
        default=Patient.Gender.UNSPECIFIED,
        help_text="Patient's gender",
    )

    class Meta:
        model = Patient
        fields: ClassVar[list[str]] = [
            "id",
            "first_name",
            "last_name",
            "date_of_birth",
            "gender",
            "mrn",
            "ward",
            "bed",
            "phone_number",
            "created_at",
            "updated_at",
        ]
        read_only_fields: ClassVar[list[str]] = ["id", "created_at", "updated_at"]

    def create(self, validated_data: dict) -> Patient:
        validated_data.setdefault("gender", Patient.Gender.UNSPECIFIED)
        return Patient.objects.create(**validated_data)

    def update(self, instance: Patient, validated_data: dict) -> Patient:
        instance.first_name = validated_data.get("first_name", instance.first_name)
        instance.last_name = validated_data.get("last_name", instance.last_name)
        instance.date_of_birth = validated_data.get(
            "date_of_birth",
            instance.date_of_birth,
        )
        instance.gender = validated_data.get("gender", instance.gender)
        instance.mrn = validated_data.get("mrn", instance.mrn)
        instance.ward = validated_data.get("ward", instance.ward)
        instance.bed = validated_data.get("bed", instance.bed)
        instance.phone_number = validated_data.get(
            "phone_number",
            instance.phone_number,
        )
        instance.save()
        return instance


class GoogleFormLinkSerializer(serializers.ModelSerializer):
    """
    Serializer for GoogleFormLink model.

    Provides read-only access to Google Form links that are displayed to all users.
    Only active forms are typically shown in the frontend.
    """

    class Meta:
        model = GoogleFormLink
        fields: ClassVar[list[str]] = [
            "id",
            "title",
            "url",
            "description",
            "display_order",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields: ClassVar[list[str]] = [
            "id",
            "created_at",
            "updated_at",
        ]
