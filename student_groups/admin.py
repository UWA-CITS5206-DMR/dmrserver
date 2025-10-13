from typing import Any, ClassVar

from django.contrib import admin

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
    OxygenSaturation,
    PainScore,
    RespiratoryRate,
)


class ObservationAdmin(admin.ModelAdmin):
    """Generic vitals observation admin configuration."""

    autocomplete_fields: ClassVar[list[str]] = ["patient", "user"]
    readonly_fields: ClassVar[list[str]] = ["created_at"]
    search_fields: ClassVar[list[str]] = [
        "patient__first_name",
        "patient__last_name",
        "user__username",
    ]
    fieldsets = (
        ("Patient Information", {"fields": ("patient", "user")}),
        ("Observation Data", {"fields": ()}),
        ("Timestamps", {"fields": ("created_at",)}),
    )

    def get_fieldsets(self, _request: object, _obj: object | None = None) -> tuple:
        # Allow subclasses to override observation fields
        observation_fields = getattr(self, "observation_fields", ())
        return (
            self.fieldsets[0],
            (self.fieldsets[1][0], {"fields": observation_fields}),
            self.fieldsets[2],
        )


class ApprovedFileInline(admin.TabularInline):
    """Inline for ApprovedFile on ImagingRequest."""

    model = ApprovedFile
    extra = 1
    autocomplete_fields: ClassVar[list[str]] = ["file"]


@admin.register(Note)
class NoteAdmin(admin.ModelAdmin):
    """Admin display for clinical notes."""

    list_display: ClassVar[list[str]] = [
        "patient",
        "user",
        "name",
        "role",
        "created_at",
        "updated_at",
    ]
    list_filter: ClassVar[list[str]] = ["user", "role", "created_at", "updated_at"]
    search_fields: ClassVar[list[str]] = [
        "patient__first_name",
        "patient__last_name",
        "user__username",
        "name",
        "role",
        "content",
    ]
    autocomplete_fields: ClassVar[list[str]] = ["patient", "user"]
    readonly_fields: ClassVar[list[str]] = ["created_at", "updated_at"]

    fieldsets = (
        ("Patient Information", {"fields": ("patient", "user")}),
        ("Recorder Info", {"fields": ("name", "role")}),
        ("Note Content", {"fields": ("content",)}),
        (
            "Timestamps",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )


@admin.register(BloodPressure)
class BloodPressureAdmin(ObservationAdmin):
    """Admin for blood pressure observations."""

    list_display: ClassVar[list[str]] = [
        "patient",
        "user",
        "systolic",
        "diastolic",
        "created_at",
    ]
    list_filter: ClassVar[list[str]] = ["user", "created_at", "systolic", "diastolic"]
    observation_fields: ClassVar[tuple[str, ...]] = ("systolic", "diastolic")


@admin.register(HeartRate)
class HeartRateAdmin(ObservationAdmin):
    """Admin for heart rate observations."""

    list_display: ClassVar[list[str]] = ["patient", "user", "heart_rate", "created_at"]
    list_filter: ClassVar[list[str]] = ["user", "created_at", "heart_rate"]
    observation_fields: ClassVar[tuple[str, ...]] = ("heart_rate",)


@admin.register(BodyTemperature)
class BodyTemperatureAdmin(ObservationAdmin):
    """Admin for body temperature observations."""

    list_display: ClassVar[list[str]] = ["patient", "user", "temperature", "created_at"]
    list_filter: ClassVar[list[str]] = ["user", "created_at", "temperature"]
    observation_fields: ClassVar[tuple[str, ...]] = ("temperature",)


@admin.register(RespiratoryRate)
class RespiratoryRateAdmin(ObservationAdmin):
    """Admin for respiratory rate observations."""

    list_display: ClassVar[list[str]] = [
        "patient",
        "user",
        "respiratory_rate",
        "created_at",
    ]
    list_filter: ClassVar[list[str]] = ["user", "created_at", "respiratory_rate"]
    observation_fields: ClassVar[tuple[str, ...]] = ("respiratory_rate",)


@admin.register(BloodSugar)
class BloodSugarAdmin(ObservationAdmin):
    """Admin for blood sugar observations."""

    list_display: ClassVar[list[str]] = ["patient", "user", "sugar_level", "created_at"]
    list_filter: ClassVar[list[str]] = ["user", "created_at", "sugar_level"]
    observation_fields: ClassVar[tuple[str, ...]] = ("sugar_level",)


@admin.register(OxygenSaturation)
class OxygenSaturationAdmin(ObservationAdmin):
    """Admin for oxygen saturation observations."""

    list_display: ClassVar[list[str]] = [
        "patient",
        "user",
        "saturation_percentage",
        "created_at",
    ]
    list_filter: ClassVar[list[str]] = ["user", "created_at", "saturation_percentage"]
    observation_fields: ClassVar[tuple[str, ...]] = ("saturation_percentage",)


@admin.register(PainScore)
class PainScoreAdmin(ObservationAdmin):
    """Admin for pain score observations."""

    list_display: ClassVar[list[str]] = ["patient", "user", "score", "created_at"]
    list_filter: ClassVar[list[str]] = ["user", "created_at", "score"]
    observation_fields: ClassVar[tuple[str, ...]] = ("score",)


@admin.register(ImagingRequest)
class ImagingRequestAdmin(admin.ModelAdmin):
    """Admin for imaging requests."""

    list_display: ClassVar[list[str]] = [
        "patient",
        "user",
        "test_type",
        "status",
        "created_at",
        "updated_at",
    ]
    list_filter: ClassVar[list[str]] = [
        "user",
        "status",
        "test_type",
        "created_at",
        "updated_at",
    ]
    search_fields: ClassVar[list[str]] = [
        "patient__first_name",
        "patient__last_name",
        "user__username",
        "test_type",
        "name",
        "role",
    ]
    autocomplete_fields: ClassVar[list[str]] = ["patient", "user"]
    readonly_fields: ClassVar[list[str]] = ["created_at", "updated_at"]
    inlines: ClassVar[list[Any]] = [ApprovedFileInline]

    fieldsets = (
        ("Patient Information", {"fields": ("patient", "user")}),
        (
            "Request Info",
            {
                "fields": (
                    "name",
                    "role",
                    "test_type",
                    "details",
                    "infection_control_precautions",
                    "imaging_focus",
                    "status",
                ),
            },
        ),
        (
            "Timestamps",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )


class ApprovedFileBloodTestInline(admin.TabularInline):
    """Inline admin for approved files in blood test requests."""

    model = ApprovedFile
    fk_name = "blood_test_request"
    extra = 1
    autocomplete_fields: ClassVar[list[str]] = ["file"]


@admin.register(BloodTestRequest)
class BloodTestRequestAdmin(admin.ModelAdmin):
    """Admin for blood test requests."""

    list_display: ClassVar[list[str]] = [
        "patient",
        "user",
        "test_type",
        "status",
        "created_at",
        "updated_at",
    ]
    list_filter: ClassVar[list[str]] = [
        "user",
        "status",
        "test_type",
        "created_at",
        "updated_at",
    ]
    search_fields: ClassVar[list[str]] = [
        "patient__first_name",
        "patient__last_name",
        "user__username",
        "test_type",
        "name",
        "role",
    ]
    autocomplete_fields: ClassVar[list[str]] = ["patient", "user"]
    readonly_fields: ClassVar[list[str]] = ["created_at", "updated_at"]
    inlines: ClassVar[list[Any]] = [ApprovedFileBloodTestInline]

    fieldsets = (
        ("Patient Information", {"fields": ("patient", "user")}),
        (
            "Request Info",
            {
                "fields": (
                    "name",
                    "role",
                    "test_type",
                    "details",
                    "status",
                ),
            },
        ),
        (
            "Timestamps",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )


@admin.register(MedicationOrder)
class MedicationOrderAdmin(admin.ModelAdmin):
    """Admin for medication orders."""

    list_display: ClassVar[list[str]] = [
        "patient",
        "user",
        "medication_name",
        "dosage",
        "created_at",
        "updated_at",
    ]
    list_filter: ClassVar[list[str]] = [
        "user",
        "medication_name",
        "created_at",
        "updated_at",
    ]
    search_fields: ClassVar[list[str]] = [
        "patient__first_name",
        "patient__last_name",
        "user__username",
        "medication_name",
    ]
    autocomplete_fields: ClassVar[list[str]] = ["patient", "user"]
    readonly_fields: ClassVar[list[str]] = ["created_at", "updated_at"]

    fieldsets = (
        ("Patient Information", {"fields": ("patient", "user")}),
        (
            "Medication Info",
            {
                "fields": (
                    "name",
                    "role",
                    "medication_name",
                    "dosage",
                    "instructions",
                ),
            },
        ),
        (
            "Timestamps",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )


@admin.register(DischargeSummary)
class DischargeSummaryAdmin(admin.ModelAdmin):
    """Admin for discharge summaries."""

    list_display: ClassVar[list[str]] = [
        "patient",
        "user",
        "diagnosis",
        "created_at",
        "updated_at",
    ]
    list_filter: ClassVar[list[str]] = ["user", "created_at", "updated_at"]
    search_fields: ClassVar[list[str]] = [
        "patient__first_name",
        "patient__last_name",
        "user__username",
        "diagnosis",
        "plan",
        "name",
        "role",
    ]
    autocomplete_fields: ClassVar[list[str]] = ["patient", "user"]
    readonly_fields: ClassVar[list[str]] = ["created_at", "updated_at"]

    fieldsets = (
        ("Patient Information", {"fields": ("patient", "user")}),
        ("Recorder Info", {"fields": ("name", "role")}),
        (
            "Discharge Summary",
            {"fields": ("diagnosis", "plan", "free_text")},
        ),
        (
            "Timestamps",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )


@admin.register(ApprovedFile)
class ApprovedFileAdmin(admin.ModelAdmin):
    """Admin for approved files."""

    list_display: ClassVar[list[str]] = ["imaging_request", "file", "page_range"]
    search_fields: ClassVar[list[str]] = [
        "imaging_request__patient__first_name",
        "imaging_request__patient__last_name",
        "file__id",
    ]
    autocomplete_fields: ClassVar[list[str]] = ["imaging_request", "file"]
