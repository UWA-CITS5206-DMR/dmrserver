from pathlib import Path
from typing import ClassVar

from rest_framework import serializers

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
        Automatically sets display_name from the uploaded file's name.
        """
        validated_data["display_name"] = validated_data["file"].name
        return super().create(validated_data)


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
            "email",
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
        instance.email = validated_data.get("email", instance.email)
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
