from rest_framework import serializers
from student_groups.models import LabRequest


class BaseModelSerializer(serializers.ModelSerializer):
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)


class LabRequestSerializer(BaseModelSerializer):
    """
    Serializer for instructors to create/manage lab requests.
    Allows instructors to set the user field when creating requests.
    """

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
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class LabRequestStatusUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for instructor to update only the status field of LabRequest.
    Used to enforce that instructors can only change status from pending to completed.
    """

    class Meta:
        model = LabRequest
        fields = ["id", "status", "updated_at"]
        read_only_fields = ["id", "updated_at"]

    def validate_status(self, value):
        """
        Only allow status transitions from pending to completed.
        """
        if self.instance and self.instance.status == "completed":
            raise serializers.ValidationError("Cannot modify a completed lab request.")
        if value not in ["pending", "completed"]:
            raise serializers.ValidationError("Invalid status value.")
        return value
