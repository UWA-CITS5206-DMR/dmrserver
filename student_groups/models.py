from typing import Any, ClassVar

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models import BaseConstraint

from patients.models import File, Patient

from .validators import ObservationValidator


class Note(models.Model):
    # Name of the doctor or person writing the note
    name = models.CharField(max_length=100, verbose_name="Doctor Name")
    role = models.CharField(max_length=50, verbose_name="Role")
    patient = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE,
        related_name="notes",
        verbose_name="Patient",
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="notes",
        verbose_name="User",
    )
    content = models.TextField(verbose_name="Content")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created At")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Updated At")

    class Meta:
        verbose_name = "Note"
        verbose_name_plural = "Notes"
        ordering: ClassVar[list[str]] = ["-created_at"]

    def __str__(self) -> str:
        return f"Note for {self.patient} by {self.name} ({self.user.username})"


class BloodPressure(models.Model):
    patient = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE,
        related_name="blood_pressures",
        verbose_name="Patient",
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="blood_pressures",
        verbose_name="User",
    )
    systolic = models.PositiveIntegerField(verbose_name="Systolic Pressure")
    diastolic = models.PositiveIntegerField(verbose_name="Diastolic Pressure")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created At")

    class Meta:
        verbose_name = "Blood Pressure"
        verbose_name_plural = "Blood Pressures"
        ordering: ClassVar[list[str]] = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.patient} - {self.systolic}/{self.diastolic} mmHg ({self.user.username})"

    def save(self, *args: object, **kwargs: object) -> None:
        self.clean()
        super().save(*args, **kwargs)

    def clean(self) -> None:
        ObservationValidator.validate_blood_pressure(
            self.patient,
            self.user,
            self.systolic,
            self.diastolic,
        )


class HeartRate(models.Model):
    patient = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE,
        related_name="heart_rates",
        verbose_name="Patient",
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="heart_rates",
        verbose_name="User",
    )
    heart_rate = models.PositiveIntegerField(verbose_name="Heart Rate (bpm)")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created At")

    class Meta:
        verbose_name = "Heart Rate"
        verbose_name_plural = "Heart Rates"
        ordering: ClassVar[list[str]] = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.patient} - {self.heart_rate} bpm ({self.user.username})"

    def save(self, *args: object, **kwargs: object) -> None:
        self.clean()
        super().save(*args, **kwargs)

    def clean(self) -> None:
        ObservationValidator.validate_heart_rate(
            self.patient,
            self.user,
            self.heart_rate,
        )


class BodyTemperature(models.Model):
    patient = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE,
        related_name="body_temperatures",
        verbose_name="Patient",
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="body_temperatures",
        verbose_name="User",
    )
    temperature = models.DecimalField(
        max_digits=4,
        decimal_places=1,
        verbose_name="Temperature (°C)",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created At")

    class Meta:
        verbose_name = "Body Temperature"
        verbose_name_plural = "Body Temperatures"
        ordering: ClassVar[list[str]] = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.patient} - {self.temperature}°C ({self.user.username})"

    def save(self, *args: object, **kwargs: object) -> None:
        self.clean()
        super().save(*args, **kwargs)

    def clean(self) -> None:
        ObservationValidator.validate_body_temperature(
            self.patient,
            self.user,
            self.temperature,
        )


class RespiratoryRate(models.Model):
    patient = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE,
        related_name="respiratory_rates",
        verbose_name="Patient",
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="respiratory_rates",
        verbose_name="User",
    )
    respiratory_rate = models.PositiveIntegerField(
        verbose_name="Respiratory Rate (breaths/min)",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created At")

    class Meta:
        verbose_name = "Respiratory Rate"
        verbose_name_plural = "Respiratory Rates"
        ordering: ClassVar[list[str]] = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.patient} - {self.respiratory_rate} breaths/min ({self.user.username})"

    def save(self, *args: object, **kwargs: object) -> None:
        self.clean()
        super().save(*args, **kwargs)

    def clean(self) -> None:
        ObservationValidator.validate_respiratory_rate(
            self.patient,
            self.user,
            self.respiratory_rate,
        )


class BloodSugar(models.Model):
    patient = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE,
        related_name="blood_sugars",
        verbose_name="Patient",
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="blood_sugars",
        verbose_name="User",
    )
    sugar_level = models.DecimalField(
        max_digits=5,
        decimal_places=1,
        verbose_name="Blood Sugar Level (mmol/L)",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created At")

    class Meta:
        verbose_name = "Blood Sugar"
        verbose_name_plural = "Blood Sugars"
        ordering: ClassVar[list[str]] = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.patient} - {self.sugar_level} mmol/L ({self.user.username})"

    def save(self, *args: object, **kwargs: object) -> None:
        self.clean()
        super().save(*args, **kwargs)

    def clean(self) -> None:
        ObservationValidator.validate_blood_sugar(
            self.patient,
            self.user,
            self.sugar_level,
        )


class OxygenSaturation(models.Model):
    patient = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE,
        related_name="oxygen_saturations",
        verbose_name="Patient",
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="oxygen_saturations",
        verbose_name="User",
    )
    saturation_percentage = models.PositiveIntegerField(
        verbose_name="Oxygen Saturation (%)",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created At")

    class Meta:
        verbose_name = "Oxygen Saturation"
        verbose_name_plural = "Oxygen Saturations"
        ordering: ClassVar[list[str]] = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.patient} - {self.saturation_percentage}% ({self.user.username})"

    def save(self, *args: object, **kwargs: object) -> None:
        self.clean()
        super().save(*args, **kwargs)

    def clean(self) -> None:
        ObservationValidator.validate_oxygen_saturation(
            self.patient,
            self.user,
            self.saturation_percentage,
        )


class PainScore(models.Model):
    patient = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE,
        related_name="pain_scores",
        verbose_name="Patient",
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="pain_scores",
        verbose_name="User",
    )
    score = models.PositiveIntegerField(verbose_name="Pain Score (0-10)")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created At")

    class Meta:
        verbose_name = "Pain Score"
        verbose_name_plural = "Pain Scores"
        ordering: ClassVar[list[str]] = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.patient} - Pain {self.score}/10 ({self.user.username})"

    def save(self, *args: object, **kwargs: object) -> None:
        self.clean()
        super().save(*args, **kwargs)

    def clean(self) -> None:
        ObservationValidator.validate_pain_score(self.patient, self.user, self.score)


class ObservationManager(models.Manager):
    @staticmethod
    @transaction.atomic
    def create_observations(validated_data: dict[str, Any]) -> dict[str, Any]:
        """
        Create observation records in a single transaction.

        :param validated_data: A dictionary containing observation data,
                               e.g., {'blood_pressure': {...}, 'heart_rate': {...}}
        :return: A dictionary of created observation instances.
        """
        created_observations: dict[str, Any] = {}
        with transaction.atomic():
            if "blood_pressure" in validated_data:
                bp_data = validated_data["blood_pressure"]
                created_observations["blood_pressure"] = BloodPressure.objects.create(
                    **bp_data,
                )

            if "heart_rate" in validated_data:
                hr_data = validated_data["heart_rate"]
                created_observations["heart_rate"] = HeartRate.objects.create(**hr_data)

            if "body_temperature" in validated_data:
                bt_data = validated_data["body_temperature"]
                created_observations["body_temperature"] = (
                    BodyTemperature.objects.create(**bt_data)
                )

            if "respiratory_rate" in validated_data:
                rr_data = validated_data["respiratory_rate"]
                created_observations["respiratory_rate"] = (
                    RespiratoryRate.objects.create(**rr_data)
                )

            if "blood_sugar" in validated_data:
                bs_data = validated_data["blood_sugar"]
                created_observations["blood_sugar"] = BloodSugar.objects.create(
                    **bs_data,
                )

            if "oxygen_saturation" in validated_data:
                os_data = validated_data["oxygen_saturation"]
                created_observations["oxygen_saturation"] = (
                    OxygenSaturation.objects.create(**os_data)
                )

            if "pain_score" in validated_data:
                ps_data = validated_data["pain_score"]
                created_observations["pain_score"] = PainScore.objects.create(**ps_data)

        return created_observations

    @staticmethod
    def get_observations_by_user_and_patient(
        user_id: int | str,
        patient_id: int | str,
        ordering: str | None = None,
    ) -> dict[str, models.QuerySet]:
        """
        Get all observations for a specific user and patient.

        :param user_id: User ID to filter by
        :param patient_id: Patient ID to filter by
        :param ordering: Optional ordering field (e.g., 'created_at' or '-created_at')
        :return: Dictionary of querysets for each observation type
        """
        if ordering is None:
            ordering = "-created_at"  # Default to newest first

        return {
            "blood_pressures": BloodPressure.objects.filter(
                user_id=user_id,
                patient_id=patient_id,
            ).order_by(ordering),
            "heart_rates": HeartRate.objects.filter(
                user_id=user_id,
                patient_id=patient_id,
            ).order_by(ordering),
            "body_temperatures": BodyTemperature.objects.filter(
                user_id=user_id,
                patient_id=patient_id,
            ).order_by(ordering),
            "respiratory_rates": RespiratoryRate.objects.filter(
                user_id=user_id,
                patient_id=patient_id,
            ).order_by(ordering),
            "blood_sugars": BloodSugar.objects.filter(
                user_id=user_id,
                patient_id=patient_id,
            ).order_by(ordering),
            "oxygen_saturations": OxygenSaturation.objects.filter(
                user_id=user_id,
                patient_id=patient_id,
            ).order_by(ordering),
            "pain_scores": PainScore.objects.filter(
                user_id=user_id,
                patient_id=patient_id,
            ).order_by(ordering),
        }


class ImagingRequest(models.Model):
    class TestType(models.TextChoices):
        X_RAY = "X-ray", "X-ray"
        CT_SCAN = "CT scan", "CT scan"
        MRI_SCAN = "MRI scan", "MRI scan"
        ULTRASOUND_SCAN = "Ultrasound scan", "Ultrasound scan"
        ECHOCARDIOGRAM = "Echocardiogram", "Echocardiogram"

    class InfectionControlPrecaution(models.TextChoices):
        AIRBORNE = "Airborne", "Airborne"
        DROPLET = "Droplet", "Droplet"
        CONTACT = "Contact", "Contact"
        CHEMOTHERAPY = "Chemotherapy", "Chemotherapy"
        NONE = "None", "None"

    STATUS_CHOICES: ClassVar[list[tuple[str, str]]] = [
        ("pending", "Pending"),
        ("completed", "Completed"),
    ]

    patient = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE,
        related_name="imaging_requests",
        verbose_name="Patient",
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="imaging_requests",
        verbose_name="User",
    )
    test_type = models.CharField(
        max_length=50,
        choices=TestType.choices,
        verbose_name="Test Type",
    )
    details = models.TextField(verbose_name="Details")
    infection_control_precautions = models.CharField(
        max_length=20,
        choices=InfectionControlPrecaution.choices,
        default=InfectionControlPrecaution.NONE,
        verbose_name="Infection Control Precautions",
    )
    imaging_focus = models.TextField(blank=True, verbose_name="Imaging Focus")
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default="pending",
        verbose_name="Status",
    )
    name = models.CharField(max_length=100, verbose_name="Name")
    role = models.CharField(max_length=50, verbose_name="Role")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created At")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Updated At")
    approved_files = models.ManyToManyField(
        File,
        through="ApprovedFile",
        related_name="imaging_requests",
        verbose_name="Approved Files",
    )

    class Meta:
        verbose_name = "Imaging Request"
        verbose_name_plural = "Imaging Requests"
        ordering: ClassVar[list[str]] = ["-created_at"]

    def __str__(self) -> str:
        return f"Imaging request for {self.patient} by {self.user.username} ({self.status})"


class ApprovedFile(models.Model):
    """
    Approved file assignment with optional manual release support.

    An ApprovedFile can originate from:
    - An ImagingRequest when instructors approve imaging results
    - A BloodTestRequest when instructors approve laboratory results
    - A manual release to a student group (represented by a shared User account)

    Exactly one origin must be set for each record.
    """

    imaging_request = models.ForeignKey(
        ImagingRequest,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="approved_files_through",
    )
    blood_test_request = models.ForeignKey(
        "BloodTestRequest",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="approved_files_through",
    )
    released_to_user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="manual_approved_files",
        help_text="Student group account granted manual access.",
    )
    released_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="manual_file_releases",
        help_text="Instructor or admin who granted manual access.",
    )
    file = models.ForeignKey(File, on_delete=models.CASCADE)
    page_range = models.CharField(
        max_length=100,
        blank=True,
        default="",
        help_text="e.g., '1-5', '7', '10-12'. Only for paginated files.",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created At")

    class Meta:
        verbose_name = "Approved File"
        verbose_name_plural = "Approved Files"
        constraints: ClassVar[list[BaseConstraint]] = [
            models.CheckConstraint(
                check=(
                    models.Q(
                        imaging_request__isnull=False,
                        blood_test_request__isnull=True,
                        released_to_user__isnull=True,
                    )
                    | models.Q(
                        imaging_request__isnull=True,
                        blood_test_request__isnull=False,
                        released_to_user__isnull=True,
                    )
                    | models.Q(
                        imaging_request__isnull=True,
                        blood_test_request__isnull=True,
                        released_to_user__isnull=False,
                    )
                ),
                name="approved_file_single_source",
            ),
            models.UniqueConstraint(
                fields=["file", "released_to_user"],
                condition=models.Q(released_to_user__isnull=False),
                name="unique_manual_file_release",
            ),
        ]

    def __str__(self) -> str:
        if self.imaging_request:
            return f"File {self.file.id} for imaging request {self.imaging_request.id}"
        if self.blood_test_request:
            return f"File {self.file.id} for blood test request {self.blood_test_request.id}"
        if self.released_to_user:
            return f"File {self.file.id} manually released to {self.released_to_user.username}"
        return f"File {self.file.id}"

    def save(self, *args: object, **kwargs: object) -> None:
        self.clean()
        super().save(*args, **kwargs)

    def clean(self) -> None:
        """
        Validate that exactly one source (imaging request, blood test request, or manual release)
        is specified.
        """

        sources_set = [
            bool(self.imaging_request),
            bool(self.blood_test_request),
            bool(self.released_to_user),
        ]

        if sum(sources_set) == 0:
            msg = (
                "ApprovedFile must be associated with an ImagingRequest, a BloodTestRequest, "
                "or be manually released to a student group."
            )
            raise ValidationError(msg)

        if sum(sources_set) > 1:
            msg = "ApprovedFile cannot be associated with multiple sources simultaneously."
            raise ValidationError(msg)


class BloodTestRequest(models.Model):
    class TestType(models.TextChoices):
        FBC = "FBC", "Full Blood Count"
        EUC = "EUC", "Electrolytes, Urea, Creatinine"
        LFTS = "LFTs", "Liver Function Tests"
        LIPASE = "Lipase", "Lipase"
        TROPONIN = "Troponin", "Troponin"
        COAG = "Coag", "Coagulation Profile"
        D_DIMER = "D-dimer", "D-dimer"
        CRP = "CRP", "C-Reactive Protein"
        VBG = "VBG", "Venous Blood Gas"
        HAPTOGLOBIN = "Haptoglobin", "Haptoglobin"
        LDH = "LDH", "Lactate Dehydrogenase"
        GROUP_AND_HOLD = "Group & Hold", "Group & Hold"
        CROSSMATCH = "Crossmatch", "Crossmatch"
        BLOOD_CULTURE = "Blood Culture", "Blood Culture"
        TFT = "TFT", "Thyroid Function Tests"

    STATUS_CHOICES: ClassVar[list[tuple[str, str]]] = [
        ("pending", "Pending"),
        ("completed", "Completed"),
    ]

    patient = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE,
        related_name="blood_test_requests",
        verbose_name="Patient",
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="blood_test_requests",
        verbose_name="User",
    )
    test_type = models.CharField(
        max_length=50,
        choices=TestType.choices,
        verbose_name="Test Type",
    )
    details = models.TextField(verbose_name="Details")
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default="pending",
        verbose_name="Status",
    )
    name = models.CharField(max_length=100, verbose_name="Name")
    role = models.CharField(max_length=50, verbose_name="Role")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created At")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Updated At")
    approved_files = models.ManyToManyField(
        File,
        through="ApprovedFile",
        related_name="blood_test_requests",
        verbose_name="Approved Files",
    )

    class Meta:
        verbose_name = "Blood Test Request"
        verbose_name_plural = "Blood Test Requests"
        ordering: ClassVar[list[str]] = ["-created_at"]

    def __str__(self) -> str:
        return f"Blood test request for {self.patient} by {self.user.username} ({self.status})"


class MedicationOrder(models.Model):
    patient = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE,
        related_name="medication_orders",
        verbose_name="Patient",
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="medication_orders",
        verbose_name="User",
    )
    medication_name = models.CharField(max_length=255, verbose_name="Medication Name")
    dosage = models.CharField(max_length=100, verbose_name="Dosage")
    instructions = models.TextField(verbose_name="Instructions")
    name = models.CharField(max_length=100, verbose_name="Name")
    role = models.CharField(max_length=50, verbose_name="Role")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created At")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Updated At")

    class Meta:
        verbose_name = "Medication Order"
        verbose_name_plural = "Medication Orders"
        ordering: ClassVar[list[str]] = ["-created_at"]

    def __str__(self) -> str:
        return f"Medication order for {self.patient} by {self.user.username}"


class DischargeSummary(models.Model):
    patient = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE,
        related_name="discharge_summaries",
        verbose_name="Patient",
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="discharge_summaries",
        verbose_name="User",
    )
    diagnosis = models.TextField(verbose_name="Diagnosis")
    plan = models.TextField(verbose_name="Plan")
    free_text = models.TextField(verbose_name="Free Text", blank=True)
    name = models.CharField(max_length=100, verbose_name="Name")
    role = models.CharField(max_length=50, verbose_name="Role")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created At")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Updated At")

    class Meta:
        verbose_name = "Discharge Summary"
        verbose_name_plural = "Discharge Summaries"
        ordering: ClassVar[list[str]] = ["-created_at"]

    def __str__(self) -> str:
        return f"Discharge summary for {self.patient} by {self.user.username}"
