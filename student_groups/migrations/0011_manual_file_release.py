from typing import Any, ClassVar

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):
    dependencies: ClassVar[list[tuple[str, str] | tuple[str, str, str]]] = [
        ("student_groups", "0010_alter_approvedfile_page_range_and_more"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="approvedfile",
            name="created_at",
            field=models.DateTimeField(
                auto_now_add=True,
                default=django.utils.timezone.now,
                verbose_name="Created At",
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="approvedfile",
            name="released_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="manual_file_releases",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="approvedfile",
            name="released_to_user",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="manual_approved_files",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.RemoveConstraint(
            model_name="approvedfile",
            name="approved_file_single_request_type",
        ),
        migrations.AddConstraint(
            model_name="approvedfile",
            constraint=models.CheckConstraint(
                check=(
                    models.Q(
                        ("imaging_request__isnull", False),
                        ("blood_test_request__isnull", True),
                        ("released_to_user__isnull", True),
                    )
                    | models.Q(
                        ("imaging_request__isnull", True),
                        ("blood_test_request__isnull", False),
                        ("released_to_user__isnull", True),
                    )
                    | models.Q(
                        ("imaging_request__isnull", True),
                        ("blood_test_request__isnull", True),
                        ("released_to_user__isnull", False),
                    )
                ),
                name="approved_file_single_source",
            ),
        ),
        migrations.AddConstraint(
            model_name="approvedfile",
            constraint=models.UniqueConstraint(
                condition=models.Q(("released_to_user__isnull", False)),
                fields=("file", "released_to_user"),
                name="unique_manual_file_release",
            ),
        ),
    ]
