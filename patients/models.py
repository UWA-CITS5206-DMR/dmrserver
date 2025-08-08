from django.db import models


class Patient(models.Model):
    first_name = models.CharField(max_length=100, verbose_name="First Name")
    last_name = models.CharField(max_length=100, verbose_name="Last Name")
    date_of_birth = models.DateField(verbose_name="Date of Birth")
    email = models.EmailField(unique=True, verbose_name="Email Address")
    phone_number = models.CharField(max_length=15, blank=True, verbose_name="Phone Number")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created At")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Updated At")

    class Meta:
        verbose_name = "Patient"
        verbose_name_plural = "Patients"
        ordering = ["last_name", "first_name"]

    def __str__(self):
        return f"{self.first_name} {self.last_name}"


class BloodPressure(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name="blood_pressures",
                                verbose_name="Patient")
    systolic = models.PositiveIntegerField(verbose_name="Systolic Pressure")
    diastolic = models.PositiveIntegerField(verbose_name="Diastolic Pressure")
    measurement_date = models.DateTimeField(auto_now_add=True, verbose_name="Measurement Date")

    class Meta:
        verbose_name = "Blood Pressure"
        verbose_name_plural = "Blood Pressures"
        ordering = ["-measurement_date"]

    def __str__(self):
        return f"{self.patient} - {self.systolic}/{self.diastolic} on {self.measurement_date}"


class LabTest(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name="lab_tests", verbose_name="Patient")
    test_name = models.CharField(max_length=200, verbose_name="Test Name")
    result = models.TextField(verbose_name="Test Result")
    test_date = models.DateTimeField(auto_now_add=True, verbose_name="Test Date")

    class Meta:
        verbose_name = "Lab Test"
        verbose_name_plural = "Lab Tests"
        ordering = ["-test_date"]

    def __str__(self):
        return f"{self.patient} - {self.test_name} on {self.test_date}"
