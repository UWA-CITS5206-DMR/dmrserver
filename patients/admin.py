"""Admin configuration for the patients app."""

from django.contrib import admin

from .models import File, Patient


class FileInline(admin.TabularInline):
    """Inline to preview related files on the patient detail page."""

    model = File
    extra = 0
    fields = (
        "display_name",
        "category",
        "file",
        "requires_pagination",
        "created_at",
    )
    readonly_fields = ("display_name", "created_at")
    show_change_link = True


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    """Admin configuration for patient basic information."""

    list_display = (
        "first_name",
        "last_name",
        "email",
        "phone_number",
        "date_of_birth",
        "created_at",
        "updated_at",
    )
    list_filter = ("created_at", "updated_at")
    search_fields = (
        "first_name",
        "last_name",
        "email",
        "phone_number",
    )
    ordering = ("last_name", "first_name")
    readonly_fields = ("created_at", "updated_at")
    inlines = [FileInline]

    fieldsets = (
        ("Basic Information", {"fields": ("first_name", "last_name", "date_of_birth")}),
        ("Contact Information", {"fields": ("email", "phone_number")}),
        (
            "Timestamps",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )


@admin.register(File)
class FileAdmin(admin.ModelAdmin):
    """Admin configuration for patient files."""

    list_display = (
        "display_name",
        "patient",
        "category",
        "requires_pagination",
        "created_at",
    )
    list_filter = ("category", "requires_pagination", "created_at")
    search_fields = (
        "display_name",
        "patient__first_name",
        "patient__last_name",
    )
    autocomplete_fields = ("patient",)
    readonly_fields = ("id", "display_name", "created_at")

    fieldsets = (
        ("Related Info", {"fields": ("patient",)}),
        (
            "File Info",
            {"fields": ("display_name", "category", "file", "requires_pagination")},
        ),
        (
            "Metadata",
            {"fields": ("id", "created_at"), "classes": ("collapse",)},
        ),
    )
