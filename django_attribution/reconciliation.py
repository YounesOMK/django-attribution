import logging
from typing import Optional

from django.contrib.auth.models import User
from django.db import transaction

from django_attribution.models import Identity
from django_attribution.trackers import CookieIdentityTracker
from django_attribution.types import AttributionHttpRequest

logger = logging.getLogger(__name__)


__all__ = ["reconcile_user_identity"]


def reconcile_user_identity(request: AttributionHttpRequest) -> Identity:
    """
    Reconciles identity state when a user authenticates.

    Handles the logic of merging anonymous browsing history with
    authenticated user accounts. If the user has an existing canonical
    identity, anonymous touchpoints and conversions are transferred to it.
    If not, the current anonymous identity becomes the user's canonical
    identity.

    Args:
        request: AttributionHttpRequest with authenticated user

    Returns:
        The canonical Identity for the authenticated user

    Note:
        Updates the identity tracker cookie to reference the canonical identity.
    """

    canonical_identity = _resolve_user_identity(request)
    request.identity_tracker.set_identity(canonical_identity)

    return canonical_identity


def _resolve_user_identity(request: AttributionHttpRequest) -> Identity:
    user = request.user
    assert user.is_authenticated

    tracker = request.identity_tracker

    current_identity = _get_current_identity_from_request(request, tracker)
    user_canonical_identity = _find_user_canonical_identity(user)

    if not current_identity:
        if not user_canonical_identity:
            logger.info(f"Creating new canonical identity for user {user.id}")

        return user_canonical_identity or _create_canonical_identity_for_user(
            user, request
        )

    if current_identity.linked_user == user:
        return current_identity.get_canonical_identity()

    if not current_identity.linked_user:
        if user_canonical_identity:
            logger.info(
                f"Merging anonymous identity {current_identity.uuid} "
                f"into user {user.id}'s canonical identity"
            )
            _merge_identity_to_canonical(current_identity, user_canonical_identity)
            return user_canonical_identity

        logger.info(f"Linking identity {current_identity.uuid} to user {user.id}")
        current_identity.linked_user = user
        current_identity.save(update_fields=["linked_user"])
        return current_identity

    if not user_canonical_identity:
        logger.info(f"Creating new canonical identity for user {user.id}")
        return _create_canonical_identity_for_user(user, request)

    return user_canonical_identity


@transaction.atomic
def _merge_identity_to_canonical(source: Identity, canonical: Identity) -> None:
    if source == canonical:
        return

    if source.is_merged():
        logger.warning(f"Source identity {source.uuid} is already merged")
        return

    source.touchpoints.update(identity=canonical)
    source.conversions.update(identity=canonical)

    source.merged_into = canonical
    source.linked_user = canonical.linked_user
    source.save(update_fields=["merged_into", "linked_user"])

    source.merged_identities.update(merged_into=canonical)


def _find_user_canonical_identity(user: User) -> Optional[Identity]:
    user_identities = Identity.objects.filter(
        linked_user=user,
        merged_into__isnull=True,
    ).oldest_first()

    if user_identities.exists():
        return user_identities.first()
    return None


def _get_current_identity_from_request(
    request: AttributionHttpRequest, tracker: CookieIdentityTracker
) -> Optional[Identity]:
    identity_ref = tracker.get_identity_reference(request)

    if not identity_ref:
        return None

    try:
        return Identity.objects.get(uuid=identity_ref)
    except Identity.DoesNotExist:
        return None


def _create_canonical_identity_for_user(
    user: User,
    request: AttributionHttpRequest,
) -> Identity:
    user_agent = request.META.get("HTTP_USER_AGENT", "")

    identity = Identity.objects.create(
        linked_user=user,
        first_visit_user_agent=user_agent,
    )
    logger.info(f"Created new canonical identity {identity.uuid} for user {user.id}")
    return identity
