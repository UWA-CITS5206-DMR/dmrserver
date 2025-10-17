# Data migration to convert test_type to test_types
from typing import Any, ClassVar

from django.db import migrations


def migrate_test_type_to_test_types(apps: Any, schema_editor: Any) -> None:
    """Convert single test_type string to test_types list."""
    BloodTestRequest = apps.get_model("student_groups", "BloodTestRequest")

    for request in BloodTestRequest.objects.all():
        # Convert single test_type to list
        if request.test_type:
            request.test_types = [request.test_type]
        else:
            request.test_types = []
        request.save(update_fields=["test_types"])


def reverse_migrate_test_types_to_test_type(apps: Any, schema_editor: Any) -> None:
    """Convert test_types list back to single test_type string."""
    BloodTestRequest = apps.get_model("student_groups", "BloodTestRequest")

    for request in BloodTestRequest.objects.all():
        # Take first test type from list, or empty string
        if request.test_types and len(request.test_types) > 0:
            request.test_type = request.test_types[0]
        else:
            request.test_type = ""
        request.save(update_fields=["test_type"])


class Migration(migrations.Migration):
    dependencies: ClassVar[list[tuple[str, str]]] = [
        ("student_groups", "0012_add_test_types_field"),
    ]

    operations: ClassVar[list[Any]] = [
        migrations.RunPython(
            migrate_test_type_to_test_types,
            reverse_code=reverse_migrate_test_types_to_test_type,
        ),
    ]
