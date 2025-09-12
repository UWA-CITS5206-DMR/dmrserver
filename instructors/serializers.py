from rest_framework import serializers
from student_groups.models import LabRequest, ApprovedFile
from patients.models import File
from core.serializers import BaseModelSerializer
from student_groups.serializers import ApprovedFileSerializer


class LabRequestSerializer(BaseModelSerializer):
    """
    Serializer for instructors to create/manage lab requests.
    Allows instructors to set the user field when creating requests.
    """

    approved_files = ApprovedFileSerializer(
        source="approvedfile_set", many=True, required=False
    )

    class Meta:
        model = LabRequest
        fields = [
            "id",
            "patient",
            "user",
            "test_type",
            "reason",
            "status",
            "created_at",
            "updated_at",
            "approved_files",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def update(self, instance, validated_data):
        approved_files_data = validated_data.pop("approvedfile_set", None)
        instance = super().update(instance, validated_data)

        if approved_files_data is not None:
            instance.approvedfile_set.all().delete()
            for approved_file_data in approved_files_data:
                file_id = approved_file_data.get("file", {}).get("id")
                page_range = approved_file_data.get("page_range")
                file = File.objects.get(id=file_id)
                ApprovedFile.objects.create(
                    lab_request=instance, file=file, page_range=page_range
                )

        return instance


class LabRequestStatusUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for instructor to update only the status field of LabRequest.
    Used to enforce that instructors can only change status from pending to completed.
    """

    approved_files = ApprovedFileSerializer(
        source="approvedfile_set", many=True, required=False
    )

    class Meta:
        model = LabRequest
        fields = ["id", "status", "updated_at", "approved_files"]
        read_only_fields = ["id", "updated_at"]

    def validate_status(self, value):
        """
        Only allow status transitions from pending to completed.
        """
        if (
            self.instance
            and self.instance.status == "completed"
            and value != "completed"
        ):
            raise serializers.ValidationError(
                "Cannot change status of a completed lab request unless it is to 'completed'."
            )
        if value not in ["pending", "completed"]:
            raise serializers.ValidationError("Invalid status value.")
        return value

    def update(self, instance, validated_data):
        approved_files_data = validated_data.pop("approvedfile_set", [])

        instance = super().update(instance, validated_data)

        if approved_files_data:
            instance.approvedfile_set.all().delete()
            for approved_file_data in approved_files_data:
                file_id = approved_file_data.get("file").get("id")
                file = File.objects.get(id=file_id)
                ApprovedFile.objects.create(
                    lab_request=instance,
                    file=file,
                    page_range=approved_file_data.get("page_range"),
                )
        elif (
            "approved_files" in self.initial_data
        ):  # If an empty list is passed, clear the files
            instance.approvedfile_set.all().delete()

        return instance
