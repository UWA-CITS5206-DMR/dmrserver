from django.core.exceptions import ValidationError

# Reasonable clinical ranges/constants
_TEMP_MIN = 30.0
_TEMP_MAX = 45.0
_RESP_RATE_MIN = 5
_RESP_RATE_MAX = 60
_BLOOD_SUGAR_MIN = 2.0  # mmol/L
_BLOOD_SUGAR_MAX = 33.0  # mmol/L
_OXY_MIN = 50
_OXY_MAX = 100
_PAIN_MIN = 0
_PAIN_MAX = 10


class ObservationValidator:
    @staticmethod
    def validate_blood_pressure(
        patient: object | None,
        user: object | None,
        systolic: int,
        diastolic: int,
    ) -> None:
        if not patient:
            msg = "Patient is required"
            raise ValidationError(msg)
        if not user:
            msg = "User is required"
            raise ValidationError(msg)
        if not isinstance(systolic, int) or systolic <= 0:
            msg = "Systolic pressure must be a positive integer"
            raise ValidationError(msg)
        if not isinstance(diastolic, int) or diastolic <= 0:
            msg = "Diastolic pressure must be a positive integer"
            raise ValidationError(msg)
        if systolic < diastolic:
            msg = "Systolic pressure cannot be less than diastolic pressure"
            raise ValidationError(msg)

    @staticmethod
    def validate_heart_rate(
        patient: object | None,
        user: object | None,
        heart_rate: int,
    ) -> None:
        if not patient:
            msg = "Patient is required"
            raise ValidationError(msg)
        if not user:
            msg = "User is required"
            raise ValidationError(msg)
        if not isinstance(heart_rate, int) or heart_rate <= 0:
            msg = "Heart rate must be a positive integer"
            raise ValidationError(msg)

    @staticmethod
    def validate_body_temperature(
        patient: object | None,
        user: object | None,
        temperature: object,
    ) -> None:
        if not patient:
            msg = "Patient is required"
            raise ValidationError(msg)
        if not user:
            msg = "User is required"
            raise ValidationError(msg)
        try:
            temp = float(temperature)
            if temp < _TEMP_MIN or temp > _TEMP_MAX:
                msg = f"Temperature value out of reasonable range ({_TEMP_MIN}-{_TEMP_MAX}°C)"
                raise ValidationError(msg)
        except (ValueError, TypeError) as err:
            # Distinguish parsing errors from errors during exception handling
            msg = "Temperature must be a valid number"
            raise ValidationError(msg) from err

    @staticmethod
    def validate_respiratory_rate(
        patient: object | None,
        user: object | None,
        respiratory_rate: int,
    ) -> None:
        if not patient:
            msg = "Patient is required"
            raise ValidationError(msg)
        if not user:
            msg = "User is required"
            raise ValidationError(msg)
        if not isinstance(respiratory_rate, int) or respiratory_rate <= 0:
            msg = "Respiratory rate must be a positive integer"
            raise ValidationError(msg)
        if respiratory_rate < _RESP_RATE_MIN or respiratory_rate > _RESP_RATE_MAX:
            msg = f"Respiratory rate value out of reasonable range ({_RESP_RATE_MIN}-{_RESP_RATE_MAX} breaths/min)"
            raise ValidationError(msg)

    @staticmethod
    def validate_blood_sugar(
        patient: object | None,
        user: object | None,
        sugar_level: object,
    ) -> None:
        if not patient:
            msg = "Patient is required"
            raise ValidationError(msg)
        if not user:
            msg = "User is required"
            raise ValidationError(msg)
        try:
            sugar = float(sugar_level)
            if sugar < _BLOOD_SUGAR_MIN or sugar > _BLOOD_SUGAR_MAX:
                msg = f"Blood sugar level out of reasonable range ({_BLOOD_SUGAR_MIN}-{_BLOOD_SUGAR_MAX} mmol/L)"
                raise ValidationError(msg)
        except (ValueError, TypeError) as err:
            msg = "Blood sugar level must be a valid number"
            raise ValidationError(msg) from err

    @staticmethod
    def validate_oxygen_saturation(
        patient: object | None,
        user: object | None,
        saturation_percentage: int,
    ) -> None:
        if not patient:
            msg = "Patient is required"
            raise ValidationError(msg)
        if not user:
            msg = "User is required"
            raise ValidationError(msg)
        if not isinstance(saturation_percentage, int) or saturation_percentage <= 0:
            msg = "Oxygen saturation must be a positive integer"
            raise ValidationError(msg)
        if saturation_percentage < _OXY_MIN or saturation_percentage > _OXY_MAX:
            msg = f"Oxygen saturation value out of reasonable range ({_OXY_MIN}-{_OXY_MAX}%)"
            raise ValidationError(msg)

    @staticmethod
    def validate_pain_score(
        patient: object | None,
        user: object | None,
        score: int,
    ) -> None:
        if not patient:
            msg = "Patient is required"
            raise ValidationError(msg)
        if not user:
            msg = "User is required"
            raise ValidationError(msg)
        if not isinstance(score, int) or score < _PAIN_MIN:
            msg = "Pain score must be a non-negative integer"
            raise ValidationError(msg)
        if score < _PAIN_MIN or score > _PAIN_MAX:
            msg = f"Pain score must be between {_PAIN_MIN} and {_PAIN_MAX}"
            raise ValidationError(msg)
