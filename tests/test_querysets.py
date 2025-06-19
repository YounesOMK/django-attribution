from unittest.mock import Mock, patch

import pytest

from django_attribution.models import Conversion
from django_attribution.shortcuts import record_conversion


@pytest.mark.django_db
def test_record_conversion_with_allowed_events_succeeds(request_with_identity):
    request_with_identity._allowed_conversion_events = {
        "signup",
        "purchase",
        "newsletter",
    }

    conversion = Conversion.objects.record(
        request_with_identity, "signup", value=0.0, currency="USD"
    )

    assert conversion is not None
    assert conversion.event == "signup"
    assert conversion.identity == request_with_identity.identity
    assert conversion.conversion_value == 0.0
    assert conversion.currency == "USD"
    assert conversion.is_confirmed is True


@pytest.mark.django_db
def test_record_conversion_with_allowed_events_multiple_events(request_with_identity):
    request_with_identity._allowed_conversion_events = {
        "signup",
        "purchase",
        "newsletter",
    }

    signup_conversion = Conversion.objects.record(request_with_identity, "signup")
    purchase_conversion = Conversion.objects.record(
        request_with_identity, "purchase", value=99.99
    )
    newsletter_conversion = Conversion.objects.record(
        request_with_identity, "newsletter"
    )

    assert signup_conversion.event == "signup"
    assert purchase_conversion.event == "purchase"
    assert purchase_conversion.conversion_value == 99.99
    assert newsletter_conversion.event == "newsletter"

    assert signup_conversion.identity == request_with_identity.identity
    assert purchase_conversion.identity == request_with_identity.identity
    assert newsletter_conversion.identity == request_with_identity.identity


@pytest.mark.django_db
def test_record_conversion_with_disallowed_event_raises_value_error(
    request_with_identity,
):
    request_with_identity._allowed_conversion_events = {"signup", "purchase"}

    with pytest.raises(ValueError) as exc_info:
        Conversion.objects.record(request_with_identity, "newsletter")

    error_message = str(exc_info.value)
    assert "Conversion event 'newsletter' not allowed" in error_message
    assert "['purchase', 'signup']" in error_message


@pytest.mark.django_db
def test_record_conversion_with_disallowed_event_logs_warning(request_with_identity):
    request_with_identity._allowed_conversion_events = {"signup", "purchase"}

    with patch("django_attribution.querysets.logger") as mock_logger:
        with pytest.raises(ValueError):
            Conversion.objects.record(request_with_identity, "newsletter")

        mock_logger.warning.assert_called_once()
        call_args = mock_logger.warning.call_args[0][0]
        assert "Attempted to record conversion 'newsletter'" in call_args
        assert "not declared in allowed events" in call_args


@pytest.mark.django_db
def test_record_conversion_without_identity_when_required_returns_none(
    request_without_identity,
):
    request_without_identity._allowed_conversion_events = {"signup"}

    result = Conversion.objects.record(request_without_identity, "signup")

    assert result is not None
    assert Conversion.objects.count() == 1


@pytest.mark.django_db
def test_record_conversion_without_identity_when_not_required_succeeds(
    request_without_identity,
):
    request_without_identity._allowed_conversion_events = {"signup"}

    conversion = Conversion.objects.record(request_without_identity, "signup")

    assert conversion is not None
    assert conversion.event == "signup"
    assert conversion.identity is None
    assert conversion.is_confirmed is True


@pytest.mark.django_db
def test_record_conversion_without_identity_logs_anonymous(request_without_identity):
    request_without_identity._allowed_conversion_events = {"signup"}

    with patch("django_attribution.querysets.logger") as mock_logger:
        conversion = Conversion.objects.record(request_without_identity, "signup")

        assert conversion is not None
        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args[0][0]
        assert "Recorded conversion 'signup'" in call_args
        assert "for identity anonymous" in call_args


@pytest.mark.django_db
def test_record_conversion_logs_successful_creation_with_identity(
    request_with_identity,
):
    request_with_identity._allowed_conversion_events = {"purchase"}

    with patch("django_attribution.querysets.logger") as mock_logger:
        conversion = Conversion.objects.record(request_with_identity, "purchase")

        assert conversion is not None
        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args[0][0]
        assert "Recorded conversion 'purchase'" in call_args
        assert f"for identity {request_with_identity.identity.uuid}" in call_args


@pytest.mark.django_db
def test_record_conversion_without_allowed_events_constraint(request_with_identity):
    conversion = Conversion.objects.record(request_with_identity, "any_event_name")

    assert conversion is not None
    assert conversion.event == "any_event_name"
    assert conversion.identity == request_with_identity.identity


@pytest.mark.django_db
def test_record_conversion_default_currency_when_not_specified(request_with_identity):
    request_with_identity._allowed_conversion_events = {"purchase"}

    conversion = Conversion.objects.record(
        request_with_identity, "purchase", value=50.00
    )

    assert conversion.currency == "EUR"


@pytest.mark.django_db
def test_record_conversion_delegates_to_queryset_record(request_with_identity):
    with patch.object(Conversion.objects, "record") as mock_record:
        mock_record.return_value = Mock()

        result = record_conversion(request_with_identity, "signup")

        mock_record.assert_called_once_with(request_with_identity, "signup")

        assert result == mock_record.return_value
