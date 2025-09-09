from rest_framework import serializers
from core.serializers import BaseModelSerializer
from .models import (
    Note,
    BloodPressure,
    HeartRate,
    BodyTemperature,
    RespiratoryRate,
    BloodSugar,
    OxygenSaturation,
    LabRequest,
    ApprovedFile,
    ObservationManager,
)
from .validators import ObservationValidator


class ApprovedFileSerializer(serializers.ModelSerializer):
    """
    Unified serializer for ApprovedFile with context-aware field selection.
    Use context={'for_student': True} to get student-friendly view.
    Use context={'for_instructor': True} to get instructor management view.
    """

    file_id = serializers.UUIDField(source="file.id")
    display_name = serializers.CharField(source="file.display_name", read_only=True)
    requires_pagination = serializers.BooleanField(
        source="file.requires_pagination", read_only=True
    )
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = ApprovedFile
        fields = [
            "id",
            "file_id",
            "display_name",
            "page_range",
            "requires_pagination",
            "file_url",
        ]

    def get_fields(self):
        fields = super().get_fields()
        context = self.context or {}

        if context.get("for_student"):
            # Students don't need file_id, but need file_url
            fields.pop("file_id", None)
        elif context.get("for_instructor"):
            # Instructors don't need file_url, but need file_id
            fields.pop("file_url", None)
        else:
            # Default: include both
            pass

        return fields

    def get_file_url(self, obj):
        request = self.context.get("request")
        if request and self.context.get("for_student"):
            return request.build_absolute_uri(
                f"/api/patients/{obj.file.patient.id}/files/{obj.file.id}/view/"
            )
        return None

    def validate(self, data):
        file_id = data.get("file", {}).get("id")
        page_range = data.get("page_range")

        if file_id:
            try:
                from patients.models import File

                file = File.objects.get(id=file_id)
                if page_range and not file.requires_pagination:
                    raise serializers.ValidationError(
                        f"File {file.display_name} does not require pagination, but a page range was provided."
                    )
                if file.requires_pagination and not page_range:
                    raise serializers.ValidationError(
                        f"File {file.display_name} requires pagination, but no page range was provided."
                    )
            except File.DoesNotExist:
                raise serializers.ValidationError(f"File with id {file_id} not found.")

        return data


class LabRequestSerializer(BaseModelSerializer):
    """
    Unified LabRequest serializer that adapts based on context.
    Use context={'for_student_read': True} for student read view
    Use context={'for_student_create': True} for student create view
    Use context={'for_instructor': True} for instructor full access
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

    def get_fields(self):
        fields = super().get_fields()
        context = self.context or {}

        if context.get("for_student_read"):
            # Students can read all fields but not modify
            for field_name, field in fields.items():
                field.read_only = True

        elif context.get("for_student_create"):
            # Students can only set these fields when creating
            read_only_fields = [
                "id",
                "user",
                "status",
                "created_at",
                "updated_at",
                "approved_files",
            ]
            for field_name in read_only_fields:
                if field_name in fields:
                    fields[field_name].read_only = True

        elif context.get("for_instructor"):
            # Instructors have full access
            fields["id"].read_only = True
            fields["created_at"].read_only = True
            fields["updated_at"].read_only = True

        return fields

    def update(self, instance, validated_data):
        # Handle approved_files updates for instructors
        approved_files_data = validated_data.pop("approvedfile_set", None)
        instance = super().update(instance, validated_data)

        if approved_files_data is not None and self.context.get("for_instructor"):
            instance.approvedfile_set.all().delete()
            for approved_file_data in approved_files_data:
                file_id = approved_file_data.get("file", {}).get("id")
                page_range = approved_file_data.get("page_range")
                from patients.models import File

                file = File.objects.get(id=file_id)
                ApprovedFile.objects.create(
                    lab_request=instance, file=file, page_range=page_range
                )

        return instance


class NoteSerializer(BaseModelSerializer):
    class Meta:
        model = Note
        fields = [
            "id",
            "patient",
            "user",
            "name",
            "content",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class BloodPressureSerializer(BaseModelSerializer):
    class Meta:
        model = BloodPressure
        fields = ["id", "patient", "user", "systolic", "diastolic", "created_at"]
        read_only_fields = ["id", "created_at"]

    def validate(self, data):
        ObservationValidator.validate_blood_pressure(
            data["patient"], data["user"], data["systolic"], data["diastolic"]
        )
        return data


class HeartRateSerializer(BaseModelSerializer):
    class Meta:
        model = HeartRate
        fields = ["id", "patient", "user", "heart_rate", "created_at"]
        read_only_fields = ["id", "created_at"]

    def validate(self, data):
        ObservationValidator.validate_heart_rate(
            data["patient"], data["user"], data["heart_rate"]
        )
        return data


class BodyTemperatureSerializer(BaseModelSerializer):
    class Meta:
        model = BodyTemperature
        fields = ["id", "patient", "user", "temperature", "created_at"]
        read_only_fields = ["id", "created_at"]

    def validate(self, data):
        ObservationValidator.validate_body_temperature(
            data["patient"], data["user"], data["temperature"]
        )
        return data


class RespiratoryRateSerializer(BaseModelSerializer):
    class Meta:
        model = RespiratoryRate
        fields = ["id", "patient", "user", "respiratory_rate", "created_at"]
        read_only_fields = ["id", "created_at"]

    def validate(self, data):
        ObservationValidator.validate_respiratory_rate(
            data["patient"], data["user"], data["respiratory_rate"]
        )
        return data


class BloodSugarSerializer(BaseModelSerializer):
    class Meta:
        model = BloodSugar
        fields = ["id", "patient", "user", "sugar_level", "created_at"]
        read_only_fields = ["id", "created_at"]

    def validate(self, data):
        ObservationValidator.validate_blood_sugar(
            data["patient"], data["user"], data["sugar_level"]
        )
        return data


class OxygenSaturationSerializer(BaseModelSerializer):
    class Meta:
        model = OxygenSaturation
        fields = ["id", "patient", "user", "saturation_percentage", "created_at"]
        read_only_fields = ["id", "created_at"]

    def validate(self, data):
        ObservationValidator.validate_oxygen_saturation(
            data["patient"], data["user"], data["saturation_percentage"]
        )
        return data


class ObservationsSerializer(serializers.Serializer):
    blood_pressure = BloodPressureSerializer(
        required=False, help_text="Blood pressure data"
    )
    heart_rate = HeartRateSerializer(required=False, help_text="Heart rate data")
    body_temperature = BodyTemperatureSerializer(
        required=False, help_text="Body temperature data"
    )
    respiratory_rate = RespiratoryRateSerializer(
        required=False, help_text="Respiratory rate data"
    )
    blood_sugar = BloodSugarSerializer(required=False, help_text="Blood sugar data")
    oxygen_saturation = OxygenSaturationSerializer(
        required=False, help_text="Oxygen saturation data"
    )

    def create(self, validated_data):
        instances = ObservationManager.create_observations(validated_data)

        created_data = {}
        if "blood_pressure" in instances:
            created_data["blood_pressure"] = BloodPressureSerializer(
                instances["blood_pressure"]
            ).data
        if "heart_rate" in instances:
            created_data["heart_rate"] = HeartRateSerializer(
                instances["heart_rate"]
            ).data
        if "body_temperature" in instances:
            created_data["body_temperature"] = BodyTemperatureSerializer(
                instances["body_temperature"]
            ).data
        if "respiratory_rate" in instances:
            created_data["respiratory_rate"] = RespiratoryRateSerializer(
                instances["respiratory_rate"]
            ).data
        if "blood_sugar" in instances:
            created_data["blood_sugar"] = BloodSugarSerializer(
                instances["blood_sugar"]
            ).data
        if "oxygen_saturation" in instances:
            created_data["oxygen_saturation"] = OxygenSaturationSerializer(
                instances["oxygen_saturation"]
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
        max_digits=4, decimal_places=1, help_text="Body temperature (°C)"
    )


class RespiratoryRateOutputSerializer(BaseObservationOutputSerializer):
    respiratory_rate = serializers.IntegerField(
        help_text="Respiratory rate (breaths per minute)"
    )


class BloodSugarOutputSerializer(BaseObservationOutputSerializer):
    sugar_level = serializers.DecimalField(
        max_digits=5, decimal_places=1, help_text="Blood sugar level (mg/dL)"
    )


class OxygenSaturationOutputSerializer(BaseObservationOutputSerializer):
    saturation_percentage = serializers.IntegerField(help_text="Oxygen saturation (%)")


class ObservationDataSerializer(serializers.Serializer):
    blood_pressures = serializers.ListField(
        child=BloodPressureOutputSerializer(),
        help_text="List of blood pressure records",
    )
    heart_rates = serializers.ListField(
        child=HeartRateOutputSerializer(), help_text="List of heart rate records"
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
