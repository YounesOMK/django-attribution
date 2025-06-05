import logging

from django.contrib.auth.models import User

from django_attribution.models import Identity
from django_attribution.querysets import IdentityQuerySet

logger = logging.getLogger(__name__)


def establish_canonical(
    unmerged_identities: "IdentityQuerySet",
    current_identity: Identity,
) -> Identity:
    canonical = unmerged_identities[0]

    merge_identities(current_identity, canonical)

    for duplicate in unmerged_identities[1:]:
        merge_identities(duplicate, canonical)
        logger.warning(
            f"Found duplicate user identity {duplicate.uuid} - merged into canonical"
        )

    return canonical


def find_unmerged_user_identities(user: User) -> "IdentityQuerySet":
    return Identity.objects.filter(
        linked_user=user,
        merged_into__isnull=True,
    ).oldest_first()  # type: ignore[attr-defined]


def merge_identities(
    from_identity: Identity,
    to_identity: Identity,
):
    from_identity.touchpoints.update(identity=to_identity)
    from_identity.conversions.update(identity=to_identity)

    from_identity.merged_into = to_identity
    from_identity.linked_user = to_identity.linked_user
    from_identity.save(update_fields=["merged_into", "linked_user"])

    logger.info(f"Merged identity {from_identity.uuid} into {to_identity.uuid}")


def link_identity_to_user(identity: Identity, user: User):
    identity.linked_user = user
    identity.save(update_fields=["linked_user"])
    logger.info(f"Linked identity {identity.uuid} to user {user.id}")


def resolve_user_identity(
    request,
    current_identity: Identity,
    tracker,
) -> Identity:
    user = request.user

    if current_identity.linked_user == user:
        return current_identity

    if current_identity.linked_user and current_identity.linked_user != user:
        logger.warning(
            f"Identity {current_identity.uuid}"
            f"linked to different user {current_identity.linked_user.id},"
            f"but request from user {user.id}"
        )
        return current_identity

    unmerged_identities = find_unmerged_user_identities(user)

    if unmerged_identities:
        canonical_identity = establish_canonical(unmerged_identities, current_identity)
        tracker.set_identity_reference(request, canonical_identity)
        logger.info(
            f"Merged {len(unmerged_identities)}"
            f"user identities into canonical "
            f"{canonical_identity.uuid}"
        )
        return canonical_identity
    else:
        link_identity_to_user(current_identity, user)
        tracker.refresh_identity(request, current_identity)
        logger.info(
            f"Linked identity {current_identity.uuid}"
            f"to already-logged-in user {user.id}"
        )
        return current_identity
