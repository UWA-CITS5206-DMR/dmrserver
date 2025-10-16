from django.apps import AppConfig


class StudentGroupsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "student_groups"

    def ready(self) -> None:
        """Import signals when app is ready."""
        # Import signals here to avoid circular import issues
        import student_groups.signals  # noqa: PLC0415,F401
