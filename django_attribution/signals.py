import logging

from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver

from .reconciliation import reconcile_user_identity

logger = logging.getLogger(__name__)


@receiver(user_logged_in)
def handle_attribution_on_login(sender, request, user, **kwargs):
    try:
        logger.info(f"Handling attribution reconciliation for user {user.id} login")

        canonical_identity = reconcile_user_identity(request)
        if canonical_identity:
            logger.info(
                f"Successfully reconciled identity for user {user.id} "
                f"to canonical identity {canonical_identity.uuid}"
            )
        else:
            logger.info(
                f"No canonical identity found"
                f" for user {user.id}, skipping reconciliation"
            )

    except Exception as e:
        logger.error(
            f"Error during attribution reconciliation for user {user.id}: {e}",
            exc_info=True,
        )
