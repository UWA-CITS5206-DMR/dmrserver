from django.contrib import admin
from .models import (
    BloodPressure,
    HeartRate,
    BodyTemperature,
    RespiratoryRate,
    BloodSugar,
    OxygenSaturation,
    PainScore,
    Note,
    LabRequest,
)


@admin.register(Note)
class NoteAdmin(admin.ModelAdmin):
    list_display = ["patient", "user", "content", "created_at", "updated_at"]
    list_filter = ["user", "created_at", "updated_at"]
    search_fields = [
        "patient__first_name",
        "patient__last_name",
        "user__username",
        "content",
    ]
    readonly_fields = ["created_at", "updated_at"]

    fieldsets = (
        ("Patient Information", {"fields": ("patient", "user")}),
        ("Note Content", {"fields": ("content",)}),
        (
            "Timestamps",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )


@admin.register(BloodPressure)
class BloodPressureAdmin(admin.ModelAdmin):
    list_display = ["patient", "user", "systolic", "diastolic", "created_at"]
    list_filter = ["user", "created_at", "systolic", "diastolic"]
    search_fields = ["patient__first_name", "patient__last_name", "user__username"]
    readonly_fields = ["created_at"]

    fieldsets = (
        ("Patient Information", {"fields": ("patient", "user")}),
        ("Blood Pressure Data", {"fields": ("systolic", "diastolic")}),
        ("Other Information", {"fields": ("created_at",)}),
    )


@admin.register(HeartRate)
class HeartRateAdmin(admin.ModelAdmin):
    list_display = ["patient", "user", "heart_rate", "created_at"]
    list_filter = ["user", "created_at", "heart_rate"]
    search_fields = ["patient__first_name", "patient__last_name", "user__username"]
    readonly_fields = ["created_at"]

    fieldsets = (
        ("Patient Information", {"fields": ("patient", "user")}),
        ("Heart Rate Data", {"fields": ("heart_rate",)}),
        ("Other Information", {"fields": ("created_at",)}),
    )


@admin.register(BodyTemperature)
class BodyTemperatureAdmin(admin.ModelAdmin):
    list_display = ["patient", "user", "temperature", "created_at"]
    list_filter = ["user", "created_at", "temperature"]
    search_fields = ["patient__first_name", "patient__last_name", "user__username"]
    readonly_fields = ["created_at"]

    fieldsets = (
        ("Patient Information", {"fields": ("patient", "user")}),
        ("Temperature Data", {"fields": ("temperature",)}),
        ("Other Information", {"fields": ("created_at",)}),
    )


@admin.register(RespiratoryRate)
class RespiratoryRateAdmin(admin.ModelAdmin):
    list_display = ["patient", "user", "respiratory_rate", "created_at"]
    list_filter = ["user", "created_at", "respiratory_rate"]
    search_fields = ["patient__first_name", "patient__last_name", "user__username"]
    readonly_fields = ["created_at"]

    fieldsets = (
        ("Patient Information", {"fields": ("patient", "user")}),
        ("Respiratory Rate Data", {"fields": ("respiratory_rate",)}),
        ("Other Information", {"fields": ("created_at",)}),
    )


@admin.register(BloodSugar)
class BloodSugarAdmin(admin.ModelAdmin):
    list_display = ["patient", "user", "sugar_level", "created_at"]
    list_filter = ["user", "created_at", "sugar_level"]
    search_fields = ["patient__first_name", "patient__last_name", "user__username"]
    readonly_fields = ["created_at"]

    fieldsets = (
        ("Patient Information", {"fields": ("patient", "user")}),
        ("Blood Sugar Data", {"fields": ("sugar_level",)}),
        ("Other Information", {"fields": ("created_at",)}),
    )


@admin.register(OxygenSaturation)
class OxygenSaturationAdmin(admin.ModelAdmin):
    list_display = ["patient", "user", "saturation_percentage", "created_at"]
    list_filter = ["user", "created_at", "saturation_percentage"]
    search_fields = ["patient__first_name", "patient__last_name", "user__username"]
    readonly_fields = ["created_at"]

    fieldsets = (
        ("Patient Information", {"fields": ("patient", "user")}),
        ("Oxygen Saturation Data", {"fields": ("saturation_percentage",)}),
        ("Other Information", {"fields": ("created_at",)}),
    )


@admin.register(PainScore)
class PainScoreAdmin(admin.ModelAdmin):
    list_display = ["patient", "user", "score", "created_at"]
    list_filter = ["user", "created_at", "score"]
    search_fields = ["patient__first_name", "patient__last_name", "user__username"]
    readonly_fields = ["created_at"]

    fieldsets = (
        ("Patient Information", {"fields": ("patient", "user")}),
        ("Pain Score Data", {"fields": ("score",)}),
        ("Other Information", {"fields": ("created_at",)}),
    )


@admin.register(LabRequest)
class LabRequestAdmin(admin.ModelAdmin):
    list_display = [
        "patient",
        "user",
        "test_type",
        "status",
        "created_at",
        "updated_at",
    ]
    list_filter = ["user", "status", "created_at", "updated_at"]
    search_fields = [
        "patient__first_name",
        "patient__last_name",
        "user__username",
        "test_type",
    ]
    readonly_fields = ["created_at", "updated_at"]

    fieldsets = (
        ("Patient Information", {"fields": ("patient", "user")}),
        ("Lab Test", {"fields": ("test_type", "status")}),
        (
            "Timestamps",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )
