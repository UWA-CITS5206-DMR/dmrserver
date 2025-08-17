from django.db import models
from django.contrib.auth.models import User
from patients.models import Patient


class Note(models.Model):
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
        return f"{self.patient} - {self.content[:50]}... ({self.user.username})"


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

    def __str__(self):
        return f"{self.patient} - {self.temperature}°C ({self.user.username})"
