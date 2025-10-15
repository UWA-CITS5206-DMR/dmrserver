from collections.abc import Mapping
from typing import Any, ClassVar

from rest_framework import serializers

from core.context import ViewContext
from core.serializers import BaseModelSerializer, UserSerializer
from patients.models import File
from patients.serializers import PatientSerializer

from .models import (
    ApprovedFile,
    BloodPressure,
    BloodSugar,
    BloodTestRequest,
    BodyTemperature,
    DischargeSummary,
    HeartRate,
    ImagingRequest,
    MedicationOrder,
    Note,
    ObservationManager,
    OxygenSaturation,
    PainScore,
    RespiratoryRate,
)
from .validators import ObservationValidator


class ApprovedFileSerializer(serializers.ModelSerializer):
    """
    Unified serializer for ApprovedFile with context-aware field selection.
    Use context={'for_student': True} to get student-friendly view.
    Use context={'for_instructor': True} to get instructor management view.

    Accepts both flat and nested file_id structures:
    - Flat: {"file_id": "uuid", "page_range": "1-5"}
    - Nested: {"file": {"id": "uuid"}, "page_range": "1-5"}
    """

    file_id = serializers.UUIDField(write_only=True, required=False)
    display_name = serializers.CharField(source="file.display_name", read_only=True)
    requires_pagination = serializers.BooleanField(
        source="file.requires_pagination",
        read_only=True,
    )
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = ApprovedFile
        fields: ClassVar[list[str]] = [
            "id",
            "file_id",
            "file",
            "display_name",
            "page_range",
            "requires_pagination",
            "file_url",
        ]
        extra_kwargs: ClassVar[dict[str, Any]] = {
            "file": {"write_only": True},
        }

    def to_representation(self, instance: ApprovedFile) -> dict[str, Any]:
        """
        Override to include file_id in read operations.
        """
        representation = super().to_representation(instance)
        representation["file_id"] = str(instance.file.id)
        return representation

    def get_fields(self) -> dict[str, Any]:
        fields = super().get_fields()
        context = self.context or {}

        if context.get(ViewContext.STUDENT_READ.value):
            # Students don't need file_id, but need file_url
            fields.pop("file_id", None)
        elif context.get(ViewContext.INSTRUCTOR_READ.value):
            # Instructors don't need file_url, but need file_id
            fields.pop("file_url", None)
        else:
            # Default: include both
            pass

        return fields

    def get_file_url(self, obj: ApprovedFile) -> str | None:
        request = self.context.get("request")
        if request and self.context.get(ViewContext.STUDENT_READ.value):
            return request.build_absolute_uri(
                f"/api/patients/{obj.file.patient.id}/files/{obj.file.id}/view/",
            )
        return None

    def to_internal_value(self, data: Mapping[str, Any]) -> dict[str, Any]:
        """
        Handle flat file_id structure by treating it as the file field.
        """
        # Make a copy to avoid mutating the original data
        data = data.copy() if hasattr(data, "copy") else dict(data)

        # Check if file_id is provided at the top level (flat structure)
        if "file_id" in data and "file" not in data:
            # Set file_id as the file field value - DRF will handle the lookup
            data["file"] = data.pop("file_id")

        return super().to_internal_value(data)

    def validate(self, data: dict[str, Any]) -> dict[str, Any]:
        """
        Validate that the file exists and pagination requirements are met.
        """
        # Get the file instance
        file_instance = data.get("file")
        page_range = data.get("page_range")

        if file_instance and isinstance(file_instance, File):
            # Validate pagination requirements
            if page_range and not file_instance.requires_pagination:
                raise serializers.ValidationError(
                    {
                        "page_range": f"File {file_instance.display_name} does not require pagination, but a page range was provided.",
                    },
                )
            if file_instance.requires_pagination and not page_range:
                raise serializers.ValidationError(
                    {
                        "page_range": f"File {file_instance.display_name} requires pagination, but no page range was provided.",
                    },
                )

        return data


class ImagingRequestSerializer(BaseModelSerializer):
    """
    Unified ImagingRequest serializer that adapts based on context.
    Use context={'for_student_read': True} for student read view
    Use context={'for_student_create': True} for student create view
    Use context={'for_instructor': True} for instructor full access
    """

    approved_files = ApprovedFileSerializer(
        source="approved_files_through",
        many=True,
        required=False,
    )

    class Meta:
        model = ImagingRequest
        fields: ClassVar[list[str]] = [
            "id",
            "patient",
            "user",
            "test_type",
            "details",
            "infection_control_precautions",
            "imaging_focus",
            "status",
            "name",
            "role",
            "created_at",
            "updated_at",
            "approved_files",
        ]
        read_only_fields: ClassVar[list[str]] = [
            "id",
            "user",
            "status",
            "created_at",
            "updated_at",
            "approved_files",
        ]

    def get_fields(self) -> dict[str, Any]:
        fields = super().get_fields()
        context = self.context or {}

        # Student read view: user is implicit, hide it.
        if context.get(ViewContext.STUDENT_READ.value):
            fields.pop("user", None)

        # Student create view: user is implicit, hide it.
        if context.get(ViewContext.STUDENT_CREATE.value):
            fields.pop("user", None)
            fields.pop("status", None)
            fields.pop("approved_files", None)

        # Instructor view: full access, no changes needed.
        if context.get(ViewContext.INSTRUCTOR_READ.value):
            # Add a field for managing approved files by their IDs
            fields["approved_file_ids"] = serializers.ListField(
                child=serializers.UUIDField(),
                write_only=True,
                required=False,
            )

        return fields

    def to_representation(self, instance: ImagingRequest) -> dict[str, Any]:
        # Customize representation for student read view
        context = self.context or {}
        if context.get(ViewContext.STUDENT_READ.value):
            self.context[ViewContext.STUDENT_READ.value] = (
                True  # For nested ApprovedFileSerializer
            )
        elif context.get(ViewContext.INSTRUCTOR_READ.value):
            self.context[ViewContext.INSTRUCTOR_READ.value] = True

        representation = super().to_representation(instance)

        if context.get(ViewContext.INSTRUCTOR_READ.value):
            representation["user"] = UserSerializer(instance.user).data
            representation["patient"] = PatientSerializer(instance.patient).data

        return representation


class NoteSerializer(BaseModelSerializer):
    class Meta:
        model = Note
        fields: ClassVar[list[str]] = [
            "id",
            "patient",
            "user",
            "name",
            "role",
            "content",
            "created_at",
            "updated_at",
        ]
        read_only_fields: ClassVar[list[str]] = [
            "id",
            "user",
            "created_at",
            "updated_at",
        ]


class BloodPressureSerializer(BaseModelSerializer):
    class Meta:
        model = BloodPressure
        fields: ClassVar[list[str]] = [
            "id",
            "patient",
            "user",
            "systolic",
            "diastolic",
            "created_at",
        ]
        read_only_fields: ClassVar[list[str]] = ["id", "created_at"]

    def validate(self, data: dict[str, Any]) -> dict[str, Any]:
        ObservationValidator.validate_blood_pressure(
            data["patient"],
            data["user"],
            data["systolic"],
            data["diastolic"],
        )
        return data


class HeartRateSerializer(BaseModelSerializer):
    class Meta:
        model = HeartRate
        fields: ClassVar[list[str]] = [
            "id",
            "patient",
            "user",
            "heart_rate",
            "created_at",
        ]
        read_only_fields: ClassVar[list[str]] = ["id", "created_at"]

    def validate(self, data: dict[str, Any]) -> dict[str, Any]:
        ObservationValidator.validate_heart_rate(
            data["patient"],
            data["user"],
            data["heart_rate"],
        )
        return data


class BodyTemperatureSerializer(BaseModelSerializer):
    class Meta:
        model = BodyTemperature
        fields: ClassVar[list[str]] = [
            "id",
            "patient",
            "user",
            "temperature",
            "created_at",
        ]
        read_only_fields: ClassVar[list[str]] = ["id", "created_at"]

    def validate(self, data: dict[str, Any]) -> dict[str, Any]:
        ObservationValidator.validate_body_temperature(
            data["patient"],
            data["user"],
            data["temperature"],
        )
        return data


class RespiratoryRateSerializer(BaseModelSerializer):
    class Meta:
        model = RespiratoryRate
        fields: ClassVar[list[str]] = [
            "id",
            "patient",
            "user",
            "respiratory_rate",
            "created_at",
        ]
        read_only_fields: ClassVar[list[str]] = ["id", "created_at"]

    def validate(self, data: dict[str, Any]) -> dict[str, Any]:
        ObservationValidator.validate_respiratory_rate(
            data["patient"],
            data["user"],
            data["respiratory_rate"],
        )
        return data


class BloodSugarSerializer(BaseModelSerializer):
    class Meta:
        model = BloodSugar
        fields: ClassVar[list[str]] = [
            "id",
            "patient",
            "user",
            "sugar_level",
            "created_at",
        ]
        read_only_fields: ClassVar[list[str]] = ["id", "created_at"]

    def validate(self, data: dict[str, Any]) -> dict[str, Any]:
        ObservationValidator.validate_blood_sugar(
            data["patient"],
            data["user"],
            data["sugar_level"],
        )
        return data


class OxygenSaturationSerializer(BaseModelSerializer):
    class Meta:
        model = OxygenSaturation
        fields: ClassVar[list[str]] = [
            "id",
            "patient",
            "user",
            "saturation_percentage",
            "created_at",
        ]
        read_only_fields: ClassVar[list[str]] = ["id", "created_at"]

    def validate(self, data: dict[str, Any]) -> dict[str, Any]:
        ObservationValidator.validate_oxygen_saturation(
            data["patient"],
            data["user"],
            data["saturation_percentage"],
        )
        return data


class PainScoreSerializer(BaseModelSerializer):
    class Meta:
        model = PainScore
        fields: ClassVar[list[str]] = ["id", "patient", "user", "score", "created_at"]
        read_only_fields: ClassVar[list[str]] = ["id", "created_at"]

    def validate(self, data: dict[str, Any]) -> dict[str, Any]:
        ObservationValidator.validate_pain_score(
            data["patient"],
            data["user"],
            data["score"],
        )
        return data


class BloodTestRequestSerializer(BaseModelSerializer):
    approved_files = ApprovedFileSerializer(
        source="approved_files_through",
        many=True,
        required=False,
    )

    class Meta:
        model = BloodTestRequest
        fields: ClassVar[list[str]] = [
            "id",
            "patient",
            "user",
            "test_type",
            "details",
            "status",
            "name",
            "role",
            "created_at",
            "updated_at",
            "approved_files",
        ]
        read_only_fields: ClassVar[list[str]] = [
            "id",
            "user",
            "status",
            "created_at",
            "updated_at",
            "approved_files",
        ]

    def to_representation(self, instance: BloodTestRequest) -> dict[str, Any]:
        context = self.context or {}
        if context.get(ViewContext.STUDENT_READ.value):
            self.context[ViewContext.STUDENT_READ.value] = True
        elif context.get(ViewContext.INSTRUCTOR_READ.value):
            self.context[ViewContext.INSTRUCTOR_READ.value] = True

        representation = super().to_representation(instance)

        if context.get(ViewContext.INSTRUCTOR_READ.value):
            representation["user"] = UserSerializer(instance.user).data
            representation["patient"] = PatientSerializer(instance.patient).data

        return representation


class ImagingRequestStatusUpdateSerializer(serializers.ModelSerializer):
    """Serializer for instructor status updates on imaging requests."""

    approved_files = ApprovedFileSerializer(
        source="approved_files_through",
        many=True,
        required=False,
    )

    class Meta:
        model = ImagingRequest
        fields: ClassVar[list[str]] = [
            "id",
            "status",
            "updated_at",
            "approved_files",
        ]
        read_only_fields: ClassVar[list[str]] = ["id", "updated_at"]

    def validate_status(self, value: object) -> object:
        if (
            self.instance
            and self.instance.status == "completed"
            and value != "completed"
        ):
            msg = (
                "Cannot change status of a completed imaging request unless it is to 'completed'."
            )
            raise serializers.ValidationError(msg)
        if value not in ["pending", "completed"]:
            msg = "Invalid status value."
            raise serializers.ValidationError(msg)
        return value

    def update(self, instance: ImagingRequest, validated_data: dict) -> ImagingRequest:
        approved_files_data = validated_data.pop("approved_files_through", [])

        instance = super().update(instance, validated_data)

        if approved_files_data:
            instance.approved_files_through.all().delete()
            for approved_file_data in approved_files_data:
                file = approved_file_data.get("file")
                page_range = approved_file_data.get("page_range", "")
                if file:
                    ApprovedFile.objects.create(
                        imaging_request=instance,
                        file=file,
                        page_range=page_range,
                    )
        elif "approved_files" in self.initial_data:
            instance.approved_files_through.all().delete()

        return instance

    def to_representation(self, instance: ImagingRequest) -> dict[str, Any]:
        serializer = ImagingRequestSerializer(instance, context=self.context)
        return serializer.data


class BloodTestRequestStatusUpdateSerializer(serializers.ModelSerializer):
    """Serializer for instructor status updates on blood test requests."""

    approved_files = ApprovedFileSerializer(
        source="approved_files_through",
        many=True,
        required=False,
    )

    class Meta:
        model = BloodTestRequest
        fields: ClassVar[list[str]] = [
            "id",
            "status",
            "updated_at",
            "approved_files",
        ]
        read_only_fields: ClassVar[list[str]] = ["id", "updated_at"]

    def validate_status(self, value: object) -> object:
        if (
            self.instance
            and self.instance.status == "completed"
            and value != "completed"
        ):
            msg = (
                "Cannot change status of a completed blood test request unless it is to 'completed'."
            )
            raise serializers.ValidationError(msg)
        if value not in ["pending", "completed"]:
            msg = "Invalid status value."
            raise serializers.ValidationError(msg)
        return value

    def update(self, instance: BloodTestRequest, validated_data: dict) -> BloodTestRequest:
        approved_files_data = validated_data.pop("approved_files_through", [])

        instance = super().update(instance, validated_data)

        if approved_files_data:
            instance.approved_files_through.all().delete()
            for approved_file_data in approved_files_data:
                file = approved_file_data.get("file")
                page_range = approved_file_data.get("page_range", "")
                if file:
                    ApprovedFile.objects.create(
                        blood_test_request=instance,
                        file=file,
                        page_range=page_range,
                    )
        elif "approved_files" in self.initial_data:
            instance.approved_files_through.all().delete()

        return instance

    def to_representation(self, instance: BloodTestRequest) -> dict[str, Any]:
        serializer = BloodTestRequestSerializer(instance, context=self.context)
        return serializer.data


class MedicationOrderSerializer(BaseModelSerializer):
    class Meta:
        model = MedicationOrder
        fields = "__all__"
        read_only_fields: ClassVar[list[str]] = [
            "id",
            "user",
            "created_at",
            "updated_at",
        ]


class DischargeSummarySerializer(BaseModelSerializer):
    class Meta:
        model = DischargeSummary
        fields = "__all__"
        read_only_fields: ClassVar[list[str]] = [
            "id",
            "user",
            "created_at",
            "updated_at",
        ]


class ObservationsSerializer(serializers.Serializer):
    blood_pressure = BloodPressureSerializer(
        required=False,
        help_text="Blood pressure data",
    )
    heart_rate = HeartRateSerializer(required=False, help_text="Heart rate data")
    body_temperature = BodyTemperatureSerializer(
        required=False,
        help_text="Body temperature data",
    )
    respiratory_rate = RespiratoryRateSerializer(
        required=False,
        help_text="Respiratory rate data",
    )
    blood_sugar = BloodSugarSerializer(required=False, help_text="Blood sugar data")
    oxygen_saturation = OxygenSaturationSerializer(
        required=False,
        help_text="Oxygen saturation data",
    )
    pain_score = PainScoreSerializer(required=False, help_text="Pain score data")

    def create(self, validated_data: dict[str, Any]) -> dict[str, Any]:
        instances = ObservationManager.create_observations(validated_data)

        created_data = {}
        if "blood_pressure" in instances:
            created_data["blood_pressure"] = BloodPressureSerializer(
                instances["blood_pressure"],
            ).data
        if "heart_rate" in instances:
            created_data["heart_rate"] = HeartRateSerializer(
                instances["heart_rate"],
            ).data
        if "body_temperature" in instances:
            created_data["body_temperature"] = BodyTemperatureSerializer(
                instances["body_temperature"],
            ).data
        if "respiratory_rate" in instances:
            created_data["respiratory_rate"] = RespiratoryRateSerializer(
                instances["respiratory_rate"],
            ).data
        if "blood_sugar" in instances:
            created_data["blood_sugar"] = BloodSugarSerializer(
                instances["blood_sugar"],
            ).data
        if "oxygen_saturation" in instances:
            created_data["oxygen_saturation"] = OxygenSaturationSerializer(
                instances["oxygen_saturation"],
            ).data
        if "pain_score" in instances:
            created_data["pain_score"] = PainScoreSerializer(
                instances["pain_score"],
            ).data

        return created_data


class BaseObservationOutputSerializer(serializers.Serializer):
    id = serializers.IntegerField(help_text="Record ID")
    patient = serializers.PrimaryKeyRelatedField(read_only=True, help_text="Patient ID")
    user = serializers.PrimaryKeyRelatedField(read_only=True, help_text="User ID")
    created_at = serializers.DateTimeField(help_text="Creation timestamp")


class BloodPressureOutputSerializer(BaseObservationOutputSerializer):
    systolic = serializers.IntegerField(help_text="Systolic blood pressure (mmHg)")
    diastolic = serializers.IntegerField(help_text="Diastolic blood pressure (mmHg)")


class HeartRateOutputSerializer(BaseObservationOutputSerializer):
    heart_rate = serializers.IntegerField(help_text="Heart rate (beats per minute)")


class BodyTemperatureOutputSerializer(BaseObservationOutputSerializer):
    temperature = serializers.DecimalField(
        max_digits=4,
        decimal_places=1,
        help_text="Body temperature (°C)",
    )


class RespiratoryRateOutputSerializer(BaseObservationOutputSerializer):
    respiratory_rate = serializers.IntegerField(
        help_text="Respiratory rate (breaths per minute)",
    )


class BloodSugarOutputSerializer(BaseObservationOutputSerializer):
    sugar_level = serializers.DecimalField(
        max_digits=5,
        decimal_places=1,
        help_text="Blood sugar level (mg/dL)",
    )


class OxygenSaturationOutputSerializer(BaseObservationOutputSerializer):
    saturation_percentage = serializers.IntegerField(help_text="Oxygen saturation (%)")


class PainScoreOutputSerializer(BaseObservationOutputSerializer):
    score = serializers.IntegerField(help_text="Pain score (0-10)")


class ObservationDataSerializer(serializers.Serializer):
    blood_pressures = serializers.ListField(
        child=BloodPressureOutputSerializer(),
        help_text="List of blood pressure records",
    )
    heart_rates = serializers.ListField(
        child=HeartRateOutputSerializer(),
        help_text="List of heart rate records",
    )
    body_temperatures = serializers.ListField(
        child=BodyTemperatureOutputSerializer(),
        help_text="List of body temperature records",
    )
    respiratory_rates = serializers.ListField(
        child=RespiratoryRateOutputSerializer(),
        help_text="List of respiratory rate records",
    )
    blood_sugars = serializers.ListField(
        child=BloodSugarOutputSerializer(),
        help_text="List of blood sugar records",
    )
    oxygen_saturations = serializers.ListField(
        child=OxygenSaturationOutputSerializer(),
        help_text="List of oxygen saturation records",
    )
    pain_scores = serializers.ListField(
        child=PainScoreOutputSerializer(),
        help_text="List of pain score records",
    )
