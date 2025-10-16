"""
Signals for student_groups app.

Handles cache invalidation when ApprovedFile records are created, updated, or deleted.
"""

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from core.cache import CacheKeyGenerator, CacheManager

from .models import ApprovedFile


@receiver(post_save, sender=ApprovedFile)
@receiver(post_delete, sender=ApprovedFile)
def invalidate_file_cache_on_approved_file_change(
    instance: ApprovedFile, **_kwargs: object
) -> None:
    """
    Invalidate file caches when ApprovedFile records change.

    This ensures that file listings for affected students are updated when files are approved
    or unapproved for their investigation requests. Only invalidates caches for users who
    should see the file, not all users.
    """
    # Get the patient ID from the approved file
    patient_id = None
    affected_user_ids = set()

    if instance.imaging_request:
        patient_id = instance.imaging_request.patient_id
        affected_user_ids.add(instance.imaging_request.user_id)
    elif instance.blood_test_request:
        patient_id = instance.blood_test_request.patient_id
        affected_user_ids.add(instance.blood_test_request.user_id)
    elif instance.released_to_user:
        # For manual releases, get patient from the file
        patient_id = instance.file.patient_id
        affected_user_ids.add(instance.released_to_user_id)

    if patient_id and affected_user_ids:
        # Invalidate file caches for this patient and specific users
        for user_id in affected_user_ids:
            keys_to_invalidate = CacheKeyGenerator.generate_invalidation_keys(
                "patients",
                "files",
                patient_id=patient_id,
                user_id=user_id,
            )

            for key in keys_to_invalidate:
                CacheManager.invalidate_cache(key)
