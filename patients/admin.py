"""Admin configuration for the patients app."""

from typing import Any, ClassVar

from django.contrib import admin

from .models import File, GoogleFormLink, Patient


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
        "mrn",
        "first_name",
        "last_name",
        "email",
        "phone_number",
        "date_of_birth",
        "gender",
        "created_at",
        "updated_at",
    )
    list_filter = ("gender", "created_at", "updated_at")
    search_fields = (
        "mrn",
        "first_name",
        "last_name",
        "email",
        "phone_number",
    )
    ordering: ClassVar[tuple[str, ...]] = ("last_name", "first_name")
    readonly_fields: ClassVar[tuple[str, ...]] = ("created_at", "updated_at")
    inlines: ClassVar[list[Any]] = [FileInline]

    fieldsets = (
        (
            "Basic Information",
            {
                "fields": (
                    "mrn",
                    "first_name",
                    "last_name",
                    "date_of_birth",
                    "gender",
                ),
            },
        ),
        ("Contact Information", {"fields": ("email", "phone_number")}),
        ("Location", {"fields": ("ward", "bed")}),
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
        "patient__mrn",
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


@admin.register(GoogleFormLink)
class GoogleFormLinkAdmin(admin.ModelAdmin):
    """Admin configuration for Google Form links."""

    list_display = (
        "title",
        "display_order",
        "is_active",
        "created_at",
        "updated_at",
    )
    list_filter = ("is_active", "created_at")
    search_fields = ("title", "description", "url")
    ordering: ClassVar[tuple[str, ...]] = ("display_order", "created_at")
    readonly_fields: ClassVar[tuple[str, ...]] = ("created_at", "updated_at")

    fieldsets = (
        (
            "Form Information",
            {
                "fields": (
                    "title",
                    "url",
                    "description",
                ),
            },
        ),
        (
            "Display Settings",
            {
                "fields": (
                    "display_order",
                    "is_active",
                ),
            },
        ),
        (
            "Timestamps",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )
