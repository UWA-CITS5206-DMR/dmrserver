from rest_framework import serializers
from student_groups.models import ImagingRequest, BloodTestRequest, ApprovedFile
from patients.models import File
from core.serializers import BaseModelSerializer, UserSerializer
from patients.serializers import PatientSerializer
from student_groups.serializers import ApprovedFileSerializer


class ImagingRequestSerializer(BaseModelSerializer):
    """
    Serializer for instructors to create/manage imaging requests.
    Allows instructors to set the user field when creating requests.
    
    Returns full user and patient details on read operations,
    while accepting IDs for write operations.
    """

    approved_files = ApprovedFileSerializer(
        source="approvedfile_set", many=True, required=False
    )

    class Meta:
        model = ImagingRequest
        fields = [
            "id",
            "patient",
            "user",
            "test_type",
            "reason",
            "status",
            "name",
            "role",
            "created_at",
            "updated_at",
            "approved_files",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def to_representation(self, instance):
        """
        Override to return full user and patient details instead of just IDs.
        """
        representation = super().to_representation(instance)
        representation["user"] = UserSerializer(instance.user).data
        representation["patient"] = PatientSerializer(instance.patient).data
        return representation

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
                    imaging_request=instance, file=file, page_range=page_range
                )

        return instance


class ImagingRequestStatusUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for instructor to update only the status field of ImagingRequest.
    Used to enforce that instructors can only change status from pending to completed.
    """

    approved_files = ApprovedFileSerializer(
        source="approvedfile_set", many=True, required=False
    )

    class Meta:
        model = ImagingRequest
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
                "Cannot change status of a completed imaging request unless it is to 'completed'."
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
                    imaging_request=instance,
                    file=file,
                    page_range=approved_file_data.get("page_range"),
                )
        elif (
            "approved_files" in self.initial_data
        ):  # If an empty list is passed, clear the files
            instance.approvedfile_set.all().delete()

        return instance


class BloodTestRequestSerializer(BaseModelSerializer):
    """
    Serializer for instructors to create/manage blood test requests.
    
    Returns full user and patient details on read operations,
    while accepting IDs for write operations.
    """

    approved_files = ApprovedFileSerializer(
        source="approvedfile_set", many=True, required=False
    )

    class Meta:
        model = BloodTestRequest
        fields = [
            "id",
            "patient",
            "user",
            "test_type",
            "reason",
            "status",
            "name",
            "role",
            "created_at",
            "updated_at",
            "approved_files",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def to_representation(self, instance):
        """
        Override to return full user and patient details instead of just IDs.
        """
        representation = super().to_representation(instance)
        representation["user"] = UserSerializer(instance.user).data
        representation["patient"] = PatientSerializer(instance.patient).data
        return representation


class BloodTestRequestStatusUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for instructor to update only the status field of BloodTestRequest.
    """

    approved_files = ApprovedFileSerializer(
        source="approvedfile_set", many=True, required=False
    )

    class Meta:
        model = BloodTestRequest
        fields = ["id", "status", "updated_at", "approved_files"]
        read_only_fields = ["id", "updated_at"]

    def validate_status(self, value):
        if (
            self.instance
            and self.instance.status == "completed"
            and value != "completed"
        ):
            raise serializers.ValidationError(
                "Cannot change status of a completed blood test request unless it is to 'completed'."
            )
        if value not in ["pending", "completed"]:
            raise serializers.ValidationError("Invalid status value.")
        return value
