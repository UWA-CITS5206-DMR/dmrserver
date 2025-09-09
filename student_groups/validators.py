from django.core.exceptions import ValidationError


class ObservationValidator:
    @staticmethod
    def validate_blood_pressure(patient, user, systolic, diastolic):
        if not patient:
            raise ValidationError("Patient is required")
        if not user:
            raise ValidationError("User is required")
        if not isinstance(systolic, int) or systolic <= 0:
            raise ValidationError("Systolic pressure must be a positive integer")
        if not isinstance(diastolic, int) or diastolic <= 0:
            raise ValidationError("Diastolic pressure must be a positive integer")
        if systolic < diastolic:
            raise ValidationError(
                "Systolic pressure cannot be less than diastolic pressure"
            )

    @staticmethod
    def validate_heart_rate(patient, user, heart_rate):
        if not patient:
            raise ValidationError("Patient is required")
        if not user:
            raise ValidationError("User is required")
        if not isinstance(heart_rate, int) or heart_rate <= 0:
            raise ValidationError("Heart rate must be a positive integer")

    @staticmethod
    def validate_body_temperature(patient, user, temperature):
        if not patient:
            raise ValidationError("Patient is required")
        if not user:
            raise ValidationError("User is required")
        try:
            temp = float(temperature)
            if temp < 30.0 or temp > 45.0:
                raise ValidationError(
                    "Temperature value out of reasonable range (30.0-45.0°C)"
                )
        except (ValueError, TypeError):
            raise ValidationError("Temperature must be a valid number")

    @staticmethod
    def validate_respiratory_rate(patient, user, respiratory_rate):
        if not patient:
            raise ValidationError("Patient is required")
        if not user:
            raise ValidationError("User is required")
        if not isinstance(respiratory_rate, int) or respiratory_rate <= 0:
            raise ValidationError("Respiratory rate must be a positive integer")
        if respiratory_rate < 5 or respiratory_rate > 60:
            raise ValidationError(
                "Respiratory rate value out of reasonable range (5-60 breaths/min)"
            )

    @staticmethod
    def validate_blood_sugar(patient, user, sugar_level):
        if not patient:
            raise ValidationError("Patient is required")
        if not user:
            raise ValidationError("User is required")
        try:
            sugar = float(sugar_level)
            if sugar < 40.0 or sugar > 600.0:
                raise ValidationError(
                    "Blood sugar level out of reasonable range (40.0-600.0 mg/dL)"
                )
        except (ValueError, TypeError):
            raise ValidationError("Blood sugar level must be a valid number")

    @staticmethod
    def validate_oxygen_saturation(patient, user, saturation_percentage):
        if not patient:
            raise ValidationError("Patient is required")
        if not user:
            raise ValidationError("User is required")
        if not isinstance(saturation_percentage, int) or saturation_percentage <= 0:
            raise ValidationError("Oxygen saturation must be a positive integer")
        if saturation_percentage < 50 or saturation_percentage > 100:
            raise ValidationError(
                "Oxygen saturation value out of reasonable range (50-100%)"
            )
