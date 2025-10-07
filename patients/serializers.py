import os
from rest_framework import serializers

from .models import Patient, File


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
        fields = [
            "id",
            "patient",
            "display_name",
            "category",
            "file",
            "requires_pagination",
            "created_at",
        ]
        read_only_fields = ["id", "patient", "display_name", "created_at"]

    def validate(self, attrs):
        """
        Validate that requires_pagination can only be True for PDF files.
        This validation runs before model.clean() to provide clear API error messages.
        """
        file_obj = attrs.get("file")
        requires_pagination = attrs.get("requires_pagination", False)

        if requires_pagination and file_obj:
            filename = file_obj.name
            ext = os.path.splitext(filename)[1].lower()
            if ext != ".pdf":
                raise serializers.ValidationError(
                    {
                        "requires_pagination": "Only PDF files can be marked for pagination. Current file type: {}".format(
                            ext or "unknown"
                        )
                    }
                )

        return attrs

    def create(self, validated_data):
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

    class Meta:
        model = Patient
        fields = [
            "id",
            "first_name",
            "last_name",
            "date_of_birth",
            "email",
            "phone_number",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def create(self, validated_data):
        return Patient.objects.create(**validated_data)

    def update(self, instance, validated_data):
        instance.first_name = validated_data.get("first_name", instance.first_name)
        instance.last_name = validated_data.get("last_name", instance.last_name)
        instance.date_of_birth = validated_data.get(
            "date_of_birth", instance.date_of_birth
        )
        instance.email = validated_data.get("email", instance.email)
        instance.phone_number = validated_data.get(
            "phone_number", instance.phone_number
        )
        instance.save()
        return instance
