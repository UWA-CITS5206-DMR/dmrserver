from django.db import models
from django.contrib.auth.models import User
from patients.models import Patient, File
from .validators import ObservationValidator
from django.db import transaction
from django.core.exceptions import ValidationError


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
        ordering = ["-created_at"]

    def __str__(self):
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
        ordering = ["-created_at"]

    def clean(self):
        ObservationValidator.validate_blood_pressure(
            self.patient, self.user, self.systolic, self.diastolic
        )

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.patient} - {self.systolic}/{self.diastolic} mmHg ({self.user.username})"


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
        ordering = ["-created_at"]

    def clean(self):
        ObservationValidator.validate_heart_rate(
            self.patient, self.user, self.heart_rate
        )

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.patient} - {self.heart_rate} bpm ({self.user.username})"


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
        max_digits=4, decimal_places=1, verbose_name="Temperature (°C)"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created At")

    class Meta:
        verbose_name = "Body Temperature"
        verbose_name_plural = "Body Temperatures"
        ordering = ["-created_at"]

    def clean(self):
        ObservationValidator.validate_body_temperature(
            self.patient, self.user, self.temperature
        )

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.patient} - {self.temperature}°C ({self.user.username})"


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
        verbose_name="Respiratory Rate (breaths/min)"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created At")

    class Meta:
        verbose_name = "Respiratory Rate"
        verbose_name_plural = "Respiratory Rates"
        ordering = ["-created_at"]

    def clean(self):
        ObservationValidator.validate_respiratory_rate(
            self.patient, self.user, self.respiratory_rate
        )

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.patient} - {self.respiratory_rate} breaths/min ({self.user.username})"


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
        max_digits=5, decimal_places=1, verbose_name="Blood Sugar Level (mg/dL)"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created At")

    class Meta:
        verbose_name = "Blood Sugar"
        verbose_name_plural = "Blood Sugars"
        ordering = ["-created_at"]

    def clean(self):
        ObservationValidator.validate_blood_sugar(
            self.patient, self.user, self.sugar_level
        )

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.patient} - {self.sugar_level} mg/dL ({self.user.username})"


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
        verbose_name="Oxygen Saturation (%)"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created At")

    class Meta:
        verbose_name = "Oxygen Saturation"
        verbose_name_plural = "Oxygen Saturations"
        ordering = ["-created_at"]

    def clean(self):
        ObservationValidator.validate_oxygen_saturation(
            self.patient, self.user, self.saturation_percentage
        )

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.patient} - {self.saturation_percentage}% ({self.user.username})"


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
        ordering = ["-created_at"]

    def clean(self):
        ObservationValidator.validate_pain_score(self.patient, self.user, self.score)

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.patient} - Pain {self.score}/10 ({self.user.username})"


class ObservationManager(models.Manager):
    @transaction.atomic
    def create_observations(validated_data):
        """
        Create observation records in a single transaction.

        :param validated_data: A dictionary containing observation data,
                               e.g., {'blood_pressure': {...}, 'heart_rate': {...}}
        :return: A dictionary of created observation instances.
        """
        created_observations = {}
        with transaction.atomic():
            if "blood_pressure" in validated_data:
                bp_data = validated_data["blood_pressure"]
                created_observations["blood_pressure"] = BloodPressure.objects.create(
                    **bp_data
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
                    **bs_data
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
    def get_observations_by_user_and_patient(user_id, patient_id, ordering=None):
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
                user_id=user_id, patient_id=patient_id
            ).order_by(ordering),
            "heart_rates": HeartRate.objects.filter(
                user_id=user_id, patient_id=patient_id
            ).order_by(ordering),
            "body_temperatures": BodyTemperature.objects.filter(
                user_id=user_id, patient_id=patient_id
            ).order_by(ordering),
            "respiratory_rates": RespiratoryRate.objects.filter(
                user_id=user_id, patient_id=patient_id
            ).order_by(ordering),
            "blood_sugars": BloodSugar.objects.filter(
                user_id=user_id, patient_id=patient_id
            ).order_by(ordering),
            "oxygen_saturations": OxygenSaturation.objects.filter(
                user_id=user_id, patient_id=patient_id
            ).order_by(ordering),
            "pain_scores": PainScore.objects.filter(
                user_id=user_id, patient_id=patient_id
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

    STATUS_CHOICES = [
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
        max_length=50, choices=TestType.choices, verbose_name="Test Type"
    )
    details = models.TextField(verbose_name="Details")
    infection_control_precautions = models.CharField(
        max_length=20,
        choices=InfectionControlPrecaution.choices,
        default=InfectionControlPrecaution.NONE,
        verbose_name="Infection Control Precautions",
    )
    imaging_focus = models.TextField(
        blank=True, verbose_name="Imaging Focus"
    )
    status = models.CharField(
        max_length=10, choices=STATUS_CHOICES, default="pending", verbose_name="Status"
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
        ordering = ["-created_at"]

    def __str__(self):
        return f"Imaging request for {self.patient} by {self.user.username} ({self.status})"


class ApprovedFile(models.Model):
    """
    Approved file with page range support for both ImagingRequest and BloodTestRequest.
    Each ApprovedFile must be associated with either an ImagingRequest OR a BloodTestRequest.
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
    file = models.ForeignKey(File, on_delete=models.CASCADE)
    page_range = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="e.g., '1-5', '7', '10-12'. Only for paginated files.",
    )

    class Meta:
        verbose_name = "Approved File"
        verbose_name_plural = "Approved Files"
        constraints = [
            models.CheckConstraint(
                check=(
                    models.Q(
                        imaging_request__isnull=False, blood_test_request__isnull=True
                    )
                    | models.Q(
                        imaging_request__isnull=True, blood_test_request__isnull=False
                    )
                ),
                name="approved_file_single_request_type",
            ),
        ]

    def clean(self):
        """
        Validate that exactly one request type is set.
        """
        if not self.imaging_request and not self.blood_test_request:
            raise ValidationError(
                "ApprovedFile must be associated with either an ImagingRequest or a BloodTestRequest."
            )
        if self.imaging_request and self.blood_test_request:
            raise ValidationError(
                "ApprovedFile cannot be associated with both ImagingRequest and BloodTestRequest."
            )

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        if self.imaging_request:
            return f"File {self.file.id} for imaging request {self.imaging_request.id}"
        elif self.blood_test_request:
            return f"File {self.file.id} for blood test request {self.blood_test_request.id}"
        return f"File {self.file.id}"


class BloodTestRequest(models.Model):
    class TestType(models.TextChoices):
        FBC = "FBC", "Full Blood Count"
        EUC = "EUC", "Electrolytes, Urea, Creatinine"
        LFTS = "LFTs", "Liver Function Tests"
        COAGS = "Coags", "Coagulation Profile"
        CRP = "CRP", "C-Reactive Protein"
        TFT = "TFT", "Thyroid Function Tests"
        GROUP_AND_HOLD = "Group and Hold", "Group and Hold"

    STATUS_CHOICES = [
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
        max_length=50, choices=TestType.choices, verbose_name="Test Type"
    )
    details = models.TextField(verbose_name="Details")
    status = models.CharField(
        max_length=10, choices=STATUS_CHOICES, default="pending", verbose_name="Status"
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
        ordering = ["-created_at"]

    def __str__(self):
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
        ordering = ["-created_at"]

    def __str__(self):
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
        ordering = ["-created_at"]

    def __str__(self):
        return f"Discharge summary for {self.patient} by {self.user.username}"
