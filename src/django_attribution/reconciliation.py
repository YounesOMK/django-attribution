import logging
from typing import Optional

from django.contrib.auth.models import User

from django_attribution.models import Identity
from django_attribution.trackers import CookieIdentityTracker

logger = logging.getLogger(__name__)


def reconcile_user_identity(request) -> Optional[Identity]:
    canonical_identity = _resolve_user_identity(request)
    if canonical_identity:
        request.attribution.tracker.set_identity(canonical_identity)
    return canonical_identity


def _resolve_user_identity(request) -> Optional[Identity]:
    user = request.user
    tracker = request.attribution.tracker

    current_identity = _get_current_identity_from_request(request, tracker)
    user_canonical_identity = _find_user_canonical_identity(user)
    utm_params = request.META.get("utm_params", {})

    # No current identity - skip to fallback logic
    if not current_identity:
        if user_canonical_identity:
            return user_canonical_identity
        if utm_params:
            return _create_canonical_identity_for_user(user)
        return None

    # Current identity belongs to this user
    if current_identity.linked_user == user:
        canonical = current_identity.get_canonical_identity()
        logger.info(f"Using user's canonical identity {canonical.uuid}")
        return canonical

    # Current identity is unlinked - we can claim it
    if not current_identity.linked_user:
        if user_canonical_identity:
            _merge_identity_to_canonical(current_identity, user_canonical_identity)
            return user_canonical_identity
        current_identity.linked_user = user
        current_identity.save(update_fields=["linked_user"])
        return current_identity

    # Current identity belongs to different user - use fallback logic
    if user_canonical_identity:
        return user_canonical_identity
    if utm_params:
        return _create_canonical_identity_for_user(user)
    return None


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

    logger.info(f"Merged identity {source.uuid} into {canonical.uuid}")


def _find_user_canonical_identity(user: User) -> Optional[Identity]:
    user_identities = Identity.objects.filter(
        linked_user=user,
        merged_into__isnull=True,
    ).oldest_first()

    if user_identities.exists():
        return user_identities.first()
    return None


def _get_current_identity_from_request(
    request, tracker: CookieIdentityTracker
) -> Optional[Identity]:
    identity_ref = tracker.get_identity_reference(request)

    if not identity_ref:
        return None

    try:
        return Identity.objects.get(uuid=identity_ref)
    except Identity.DoesNotExist:
        return None


def _create_canonical_identity_for_user(user: User) -> Identity:
    identity = Identity.objects.create(linked_user=user)
    logger.info(f"Created new canonical identity {identity.uuid} for user {user.id}")
    return identity
