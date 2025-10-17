# Remove old test_type field and make test_types non-nullable
from typing import Any, ClassVar

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies: ClassVar[list[tuple[str, str]]] = [
        ("patients", "0008_remove_patient_email"),
        ("student_groups", "0013_migrate_test_type_data"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations: ClassVar[list[Any]] = [
        # Remove the old test_type field
        migrations.RemoveField(
            model_name="bloodtestrequest",
            name="test_type",
        ),
        # Make test_types non-nullable now that data is migrated
        migrations.AlterField(
            model_name="bloodtestrequest",
            name="test_types",
            field=models.JSONField(
                help_text="List of blood test types to be performed",
                verbose_name="Test Types",
            ),
        ),
        # Re-add constraints that were modified
        migrations.RemoveConstraint(
            model_name="approvedfile",
            name="approved_file_single_source",
        ),
        migrations.AlterField(
            model_name="approvedfile",
            name="released_by",
            field=models.ForeignKey(
                blank=True,
                help_text="Instructor or admin who granted manual access.",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="manual_file_releases",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name="approvedfile",
            name="released_to_user",
            field=models.ForeignKey(
                blank=True,
                help_text="Student group account granted manual access.",
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="manual_approved_files",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name="bloodsugar",
            name="sugar_level",
            field=models.DecimalField(
                decimal_places=1,
                max_digits=5,
                verbose_name="Blood Sugar Level (mmol/L)",
            ),
        ),
        migrations.AddConstraint(
            model_name="approvedfile",
            constraint=models.CheckConstraint(
                condition=models.Q(
                    models.Q(
                        ("blood_test_request__isnull", True),
                        ("imaging_request__isnull", False),
                        ("released_to_user__isnull", True),
                    ),
                    models.Q(
                        ("blood_test_request__isnull", False),
                        ("imaging_request__isnull", True),
                        ("released_to_user__isnull", True),
                    ),
                    models.Q(
                        ("blood_test_request__isnull", True),
                        ("imaging_request__isnull", True),
                        ("released_to_user__isnull", False),
                    ),
                    _connector="OR",
                ),
                name="approved_file_single_source",
            ),
        ),
    ]
