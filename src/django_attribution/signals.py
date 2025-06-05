import logging

from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver

from .reconciliation import resolve_user_identity

logger = logging.getLogger(__name__)


@receiver(user_logged_in)
def handle_attribution_on_login(sender, request, user, **kwargs):
    if not hasattr(request, "attribution"):
        logger.warning("Attribution middleware not found during login - skipping merge")
        return

    current_identity = request.attribution.identity
    tracker = request.attribution.tracker

    resolved_identity = resolve_user_identity(request, current_identity, tracker)

    if resolved_identity != current_identity:
        request.attribution.identity = resolved_identity
        logger.info(f"Updated attribution identity during login for user {user.id}")
    else:
        tracker.refresh_identity(request, current_identity)
        logger.debug(f"Refreshed attribution cookie for user {user.id}")
