from django.contrib import admin
from .models import Patient, File

class FileInline(admin.TabularInline):
    model = File
    extra = 0
    fields = ("display_name", "file", "requires_pagination", "created_at")
    readonly_fields = ("display_name","created_at",)
    show_change_link = True

@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ("first_name", "last_name", "date_of_birth", "email", "phone_number", "created_at", "updated_at")
    search_fields = ("first_name", "last_name", "email", "phone_number")
    list_filter = ("created_at", "updated_at")
    ordering = ("last_name", "first_name")
    inlines = [FileInline]
    date_hierarchy = "created_at"

@admin.register(File)
class FileAdmin(admin.ModelAdmin):
    list_display = ("display_name", "patient", "requires_pagination", "created_at")
    list_filter = ("requires_pagination", "created_at")
    search_fields = ("display_name", "patient__first_name", "patient__last_name")
    autocomplete_fields = ("patient",)
    readonly_fields = ("created_at",)