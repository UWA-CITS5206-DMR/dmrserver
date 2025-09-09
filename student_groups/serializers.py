from rest_framework import serializers
from .models import (
    Note,
    BloodPressure,
    HeartRate,
    BodyTemperature,
    RespiratoryRate,
    BloodSugar,
    OxygenSaturation,
    ObservationManager,
    LabRequest,
)
from .validators import ObservationValidator


class BaseModelSerializer(serializers.ModelSerializer):
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)


class NoteSerializer(BaseModelSerializer):
    class Meta:
        model = Note
        fields = ["id", "patient", "user", "content", "created_at", "updated_at"]
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


class LabRequestSerializer(BaseModelSerializer):
    class Meta:
        model = LabRequest
        fields = [
            "id",
            "patient",
            "user",
            "test_type",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "user"]


class LabRequestStatusUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for instructor to update only the status field of LabRequest.
    Used to enforce that instructors can only change status from pending to completed.
    """

    class Meta:
        model = LabRequest
        fields = ["status"]

    def validate_status(self, value):
        """Ensure status can only be changed from pending to completed"""
        if self.instance and self.instance.status == "completed":
            raise serializers.ValidationError(
                "Cannot modify status of an already completed request."
            )
        if value not in ["pending", "completed"]:
            raise serializers.ValidationError(
                "Status must be either 'pending' or 'completed'."
            )
        return value
