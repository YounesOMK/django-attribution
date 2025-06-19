import pytest
from django.utils import timezone

from django_attribution.models import Conversion, Identity, Touchpoint


@pytest.mark.django_db
def test_identity_string_representation_anonymous():
    identity = Identity.objects.create()

    expected_str = f"Identity {identity.uuid} (Anonymous)"
    assert str(identity) == expected_str


@pytest.mark.django_db
def test_identity_string_representation_with_user(authenticated_user):
    identity = Identity.objects.create(linked_user=authenticated_user)

    expected_str = f"Identity {identity.uuid} (User: {authenticated_user.username})"
    assert str(identity) == expected_str


@pytest.mark.django_db
def test_timestamps_auto_set_on_creation():
    before_creation = timezone.now()
    identity = Identity.objects.create()
    after_creation = timezone.now()

    assert before_creation <= identity.created_at <= after_creation
    assert before_creation <= identity.updated_at <= after_creation


@pytest.mark.django_db
def test_canonical_identity_methods_for_unmerged_identity():
    identity = Identity.objects.create()

    assert identity.is_canonical() is True
    assert identity.is_merged() is False
    assert identity.get_canonical_identity() == identity


@pytest.mark.django_db
def test_canonical_identity_methods_for_merged_identity():
    canonical_identity = Identity.objects.create()
    merged_identity = Identity.objects.create(merged_into=canonical_identity)

    assert canonical_identity.is_canonical() is True
    assert canonical_identity.is_merged() is False
    assert canonical_identity.get_canonical_identity() == canonical_identity

    assert merged_identity.is_canonical() is False
    assert merged_identity.is_merged() is True
    assert merged_identity.get_canonical_identity() == canonical_identity


@pytest.mark.django_db
def test_flat_merge_structure():
    from django_attribution.reconciliation import _merge_identity_to_canonical

    canonical_identity = Identity.objects.create()
    identity_a = Identity.objects.create()
    identity_b = Identity.objects.create()

    _merge_identity_to_canonical(identity_a, canonical_identity)
    _merge_identity_to_canonical(identity_b, canonical_identity)

    assert identity_a.get_canonical_identity() == canonical_identity
    assert identity_b.get_canonical_identity() == canonical_identity
    assert canonical_identity.get_canonical_identity() == canonical_identity

    assert identity_a.merged_into == canonical_identity
    assert identity_b.merged_into == canonical_identity


@pytest.mark.django_db
def test_touchpoint_string_representation_with_utm_source():
    identity = Identity.objects.create()
    touchpoint = Touchpoint.objects.create(
        identity=identity, url="https://example.com", utm_source="google"
    )

    expected_str = f"google ({touchpoint.created_at})"
    assert str(touchpoint) == expected_str


@pytest.mark.django_db
def test_touchpoint_string_representation_without_utm_source():
    identity = Identity.objects.create()
    touchpoint = Touchpoint.objects.create(identity=identity, url="https://example.com")

    expected_str = f"direct ({touchpoint.created_at})"
    assert str(touchpoint) == expected_str


@pytest.mark.django_db
def test_touchpoint_string_representation_with_empty_utm_source():
    identity = Identity.objects.create()
    touchpoint = Touchpoint.objects.create(
        identity=identity, url="https://example.com", utm_source=""
    )

    expected_str = f"direct ({touchpoint.created_at})"
    assert str(touchpoint) == expected_str


@pytest.mark.django_db
def test_touchpoint_default_ordering():
    identity = Identity.objects.create()

    touchpoint1 = Touchpoint.objects.create(
        identity=identity, url="https://example.com/1"
    )
    touchpoint2 = Touchpoint.objects.create(
        identity=identity, url="https://example.com/2"
    )
    touchpoint3 = Touchpoint.objects.create(
        identity=identity, url="https://example.com/3"
    )

    touchpoints = list(Touchpoint.objects.all())

    assert touchpoints[0] == touchpoint3
    assert touchpoints[1] == touchpoint2
    assert touchpoints[2] == touchpoint1


@pytest.mark.django_db
def test_conversion_string_representation_without_value():
    identity = Identity.objects.create()
    conversion = Conversion.objects.create(identity=identity, event="signup")

    expected_str = f"signup - {conversion.created_at}"
    assert str(conversion) == expected_str


@pytest.mark.django_db
def test_conversion_string_representation_with_value():
    identity = Identity.objects.create()
    conversion = Conversion.objects.create(
        identity=identity, event="purchase", conversion_value=99.99, currency="USD"
    )

    expected_str = f"purchase (USD 99.99) - {conversion.created_at}"
    assert str(conversion) == expected_str


@pytest.mark.django_db
def test_conversion_string_representation_with_zero_value():
    identity = Identity.objects.create()
    conversion = Conversion.objects.create(
        identity=identity, event="free_trial", conversion_value=0.00, currency="EUR"
    )

    expected_str = f"free_trial (EUR 0.00) - {conversion.created_at}"
    assert str(conversion) == expected_str


@pytest.mark.django_db
def test_conversion_default_currency():
    identity = Identity.objects.create()
    conversion = Conversion.objects.create(identity=identity, event="purchase")

    # Should use the default currency from settings
    assert conversion.currency == "EUR"


@pytest.mark.django_db
def test_conversion_default_ordering():
    identity = Identity.objects.create()

    conversion1 = Conversion.objects.create(identity=identity, event="signup")
    conversion2 = Conversion.objects.create(identity=identity, event="purchase")
    conversion3 = Conversion.objects.create(identity=identity, event="renewal")

    # Should be ordered by newest first (most recent created_at first)
    conversions = list(Conversion.objects.all())

    assert conversions[0] == conversion3  # Most recent
    assert conversions[1] == conversion2
    assert conversions[2] == conversion1  # Oldest
