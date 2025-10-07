from django.contrib import admin

from .models import (
    ApprovedFile,
    BloodPressure,
    HeartRate,
    BodyTemperature,
    RespiratoryRate,
    BloodSugar,
    OxygenSaturation,
    PainScore,
    Note,
    ImagingRequest,
    BloodTestRequest,
    MedicationOrder,
    DischargeSummary,
)


class ObservationAdmin(admin.ModelAdmin):
    """Generic vitals observation admin configuration."""

    autocomplete_fields = ["patient", "user"]
    readonly_fields = ["created_at"]
    search_fields = [
        "patient__first_name",
        "patient__last_name",
        "user__username",
    ]
    fieldsets = (
        ("Patient Information", {"fields": ("patient", "user")}),
        ("Observation Data", {"fields": ()}),
        ("Timestamps", {"fields": ("created_at",)}),
    )

    def get_fieldsets(self, request, obj=None):
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
    autocomplete_fields = ["file"]


@admin.register(Note)
class NoteAdmin(admin.ModelAdmin):
    """Admin display for clinical notes."""

    list_display = [
        "patient",
        "user",
        "name",
        "role",
        "created_at",
        "updated_at",
    ]
    list_filter = ["user", "role", "created_at", "updated_at"]
    search_fields = [
        "patient__first_name",
        "patient__last_name",
        "user__username",
        "name",
        "role",
        "content",
    ]
    autocomplete_fields = ["patient", "user"]
    readonly_fields = ["created_at", "updated_at"]

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

    list_display = ["patient", "user", "systolic", "diastolic", "created_at"]
    list_filter = ["user", "created_at", "systolic", "diastolic"]
    observation_fields = ("systolic", "diastolic")


@admin.register(HeartRate)
class HeartRateAdmin(ObservationAdmin):
    """Admin for heart rate observations."""

    list_display = ["patient", "user", "heart_rate", "created_at"]
    list_filter = ["user", "created_at", "heart_rate"]
    observation_fields = ("heart_rate",)


@admin.register(BodyTemperature)
class BodyTemperatureAdmin(ObservationAdmin):
    """Admin for body temperature observations."""

    list_display = ["patient", "user", "temperature", "created_at"]
    list_filter = ["user", "created_at", "temperature"]
    observation_fields = ("temperature",)


@admin.register(RespiratoryRate)
class RespiratoryRateAdmin(ObservationAdmin):
    """Admin for respiratory rate observations."""

    list_display = ["patient", "user", "respiratory_rate", "created_at"]
    list_filter = ["user", "created_at", "respiratory_rate"]
    observation_fields = ("respiratory_rate",)


@admin.register(BloodSugar)
class BloodSugarAdmin(ObservationAdmin):
    """Admin for blood sugar observations."""

    list_display = ["patient", "user", "sugar_level", "created_at"]
    list_filter = ["user", "created_at", "sugar_level"]
    observation_fields = ("sugar_level",)


@admin.register(OxygenSaturation)
class OxygenSaturationAdmin(ObservationAdmin):
    """Admin for oxygen saturation observations."""

    list_display = ["patient", "user", "saturation_percentage", "created_at"]
    list_filter = ["user", "created_at", "saturation_percentage"]
    observation_fields = ("saturation_percentage",)


@admin.register(PainScore)
class PainScoreAdmin(ObservationAdmin):
    """Admin for pain score observations."""

    list_display = ["patient", "user", "score", "created_at"]
    list_filter = ["user", "created_at", "score"]
    observation_fields = ("score",)


@admin.register(ImagingRequest)
class ImagingRequestAdmin(admin.ModelAdmin):
    """Admin for imaging requests."""

    list_display = [
        "patient",
        "user",
        "test_type",
        "status",
        "created_at",
        "updated_at",
    ]
    list_filter = ["user", "status", "test_type", "created_at", "updated_at"]
    search_fields = [
        "patient__first_name",
        "patient__last_name",
        "user__username",
        "test_type",
        "name",
        "role",
    ]
    autocomplete_fields = ["patient", "user"]
    readonly_fields = ["created_at", "updated_at"]
    inlines = [ApprovedFileInline]

    fieldsets = (
        ("Patient Information", {"fields": ("patient", "user")}),
        ("Request Info", {"fields": ("name", "role", "test_type", "reason", "status")}),
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
    autocomplete_fields = ["file"]


@admin.register(BloodTestRequest)
class BloodTestRequestAdmin(admin.ModelAdmin):
    """Admin for blood test requests."""

    list_display = [
        "patient",
        "user",
        "test_type",
        "status",
        "created_at",
        "updated_at",
    ]
    list_filter = ["user", "status", "test_type", "created_at", "updated_at"]
    search_fields = [
        "patient__first_name",
        "patient__last_name",
        "user__username",
        "test_type",
        "name",
        "role",
    ]
    autocomplete_fields = ["patient", "user"]
    readonly_fields = ["created_at", "updated_at"]
    inlines = [ApprovedFileBloodTestInline]

    fieldsets = (
        ("Patient Information", {"fields": ("patient", "user")}),
        (
            "Request Info",
            {
                "fields": (
                    "name",
                    "role",
                    "test_type",
                    "reason",
                    "status",
                )
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

    list_display = [
        "patient",
        "user",
        "medication_name",
        "dosage",
        "created_at",
        "updated_at",
    ]
    list_filter = ["user", "medication_name", "created_at", "updated_at"]
    search_fields = [
        "patient__first_name",
        "patient__last_name",
        "user__username",
        "medication_name",
    ]
    autocomplete_fields = ["patient", "user"]
    readonly_fields = ["created_at", "updated_at"]

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
                )
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

    list_display = [
        "patient",
        "user",
        "diagnosis",
        "created_at",
        "updated_at",
    ]
    list_filter = ["user", "created_at", "updated_at"]
    search_fields = [
        "patient__first_name",
        "patient__last_name",
        "user__username",
        "diagnosis",
        "plan",
        "name",
        "role",
    ]
    autocomplete_fields = ["patient", "user"]
    readonly_fields = ["created_at", "updated_at"]

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

    list_display = ["imaging_request", "file", "page_range"]
    search_fields = [
        "imaging_request__patient__first_name",
        "imaging_request__patient__last_name",
        "file__id",
    ]
    autocomplete_fields = ["imaging_request", "file"]
