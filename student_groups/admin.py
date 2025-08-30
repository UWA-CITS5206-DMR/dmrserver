from django.contrib import admin
from .models import BloodPressure, HeartRate, BodyTemperature, Note


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
