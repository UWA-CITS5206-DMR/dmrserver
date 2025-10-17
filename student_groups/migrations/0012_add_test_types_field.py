# Generated migration for multi blood test types
from typing import Any, ClassVar

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies: ClassVar[list[tuple[str, str]]] = [
        ("patients", "0008_remove_patient_email"),
        ("student_groups", "0011_manual_file_release"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations: ClassVar[list[Any]] = [
        # Step 1: Add new test_types field as nullable first
        migrations.AddField(
            model_name="bloodtestrequest",
            name="test_types",
            field=models.JSONField(
                null=True,
                blank=True,
                help_text="List of blood test types to be performed",
                verbose_name="Test Types",
            ),
        ),
    ]
