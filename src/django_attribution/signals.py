import logging
from typing import Optional

from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver

from .models import Identity

logger = logging.getLogger(__name__)


@receiver(user_logged_in)
def handle_attribution_on_login(sender, request, user, **kwargs):
    if not hasattr(request, "attribution"):
        logger.warning("Attribution middleware not found during login - skipping merge")
        return

    current_identity = request.attribution.identity
    tracker = request.attribution.tracker

    if current_identity.linked_user == user:
        request.attribution.refresh_identity()
        logger.debug(f"Refreshed attribution cookie for user {user.id}")
        return

    existing_user_identity = _find_existing_user_identity(user)

    if existing_user_identity:
        _merge_identities(
            from_identity=current_identity, to_identity=existing_user_identity
        )
        tracker.set_identity_reference(request, existing_user_identity)
        request.attribution.identity = existing_user_identity
        logger.info(
            "Merged anonymous identity"
            "{current_identity.uuid} into user"
            "identity {existing_user_identity.uuid}"
        )

    else:
        _link_identity_to_user(current_identity, user)
        request.attribution.refresh_identity()
        logger.info(f"Linked identity {current_identity.uuid} to user {user.id}")


def _find_existing_user_identity(user) -> Optional[Identity]:
    """Find the canonical identity already linked to this user"""
    return Identity.objects.filter(
        linked_user=user,
        merged_into__isnull=True,
    ).first()


def _merge_identities(from_identity: Identity, to_identity: Identity):
    from_identity.touchpoints.update(identity=to_identity)
    from_identity.conversions.update(identity=to_identity)

    from_identity.merged_into = to_identity
    from_identity.save(update_fields=["merged_into"])

    logger.info(f"Merged identity {from_identity.uuid} into {to_identity.uuid}")


def _link_identity_to_user(identity: Identity, user):
    identity.linked_user = user
    identity.save(update_fields=["linked_user"])
    logger.info(f"Linked identity {identity.uuid} to user {user.id}")
