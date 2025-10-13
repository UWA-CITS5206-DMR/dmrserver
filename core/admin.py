from django.contrib import admin
from .models import MultiDeviceToken


@admin.register(MultiDeviceToken)
class MultiDeviceTokenAdmin(admin.ModelAdmin):
    list_display = ("key", "user", "created")
    list_filter = ("created",)
    search_fields = ("user__username",)
    readonly_fields = ("key", "created")
