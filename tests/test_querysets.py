from unittest.mock import Mock, patch

import pytest

from django_attribution.models import Event
from django_attribution.shortcuts import record_event


@pytest.mark.django_db
def test_record_event_with_allowed_events_succeeds(request_with_identity):
    request_with_identity._allowed_events = {
        "signup",
        "purchase",
        "newsletter",
    }

    event = Event.objects.record(
        request_with_identity, "signup", monetary_value=0.0, currency="USD"
    )

    assert event is not None
    assert event.name == "signup"
    assert event.identity == request_with_identity.identity
    assert event.monetary_value == 0.0
    assert event.currency == "USD"
    assert event.is_confirmed is True


@pytest.mark.django_db
def test_record_event_with_allowed_events_multiple_events(request_with_identity):
    request_with_identity._allowed_events = {
        "signup",
        "purchase",
        "newsletter",
    }

    signup_event = Event.objects.record(request_with_identity, "signup")
    purchase_event = Event.objects.record(
        request_with_identity, "purchase", monetary_value=99.99
    )
    newsletter_event = Event.objects.record(request_with_identity, "newsletter")

    assert signup_event.name == "signup"
    assert purchase_event.name == "purchase"
    assert purchase_event.monetary_value == 99.99
    assert newsletter_event.name == "newsletter"

    assert signup_event.identity == request_with_identity.identity
    assert purchase_event.identity == request_with_identity.identity
    assert newsletter_event.identity == request_with_identity.identity


@pytest.mark.django_db
def test_record_event_with_disallowed_event_raises_value_error(
    request_with_identity,
):
    request_with_identity._allowed_events = {"signup", "purchase"}

    with pytest.raises(ValueError) as exc_info:
        Event.objects.record(request_with_identity, "newsletter")

    error_message = str(exc_info.value)
    assert "Event 'newsletter' not allowed" in error_message
    assert "['purchase', 'signup']" in error_message


@pytest.mark.django_db
def test_record_event_with_disallowed_event_logs_warning(request_with_identity):
    request_with_identity._allowed_events = {"signup", "purchase"}

    with patch("django_attribution.querysets.logger") as mock_logger:
        with pytest.raises(ValueError):
            Event.objects.record(request_with_identity, "newsletter")

        mock_logger.warning.assert_called_once()
        call_args = mock_logger.warning.call_args[0][0]
        assert "Attempted to record event 'newsletter'" in call_args
        assert "not declared in allowed events" in call_args


@pytest.mark.django_db
def test_record_event_without_identity_when_required_returns_none(
    request_without_identity,
):
    request_without_identity._allowed_events = {"signup"}

    result = Event.objects.record(request_without_identity, "signup")

    assert result is not None
    assert Event.objects.count() == 1


@pytest.mark.django_db
def test_record_event_without_identity_when_not_required_succeeds(
    request_without_identity,
):
    request_without_identity._allowed_events = {"signup"}

    event = Event.objects.record(request_without_identity, "signup")

    assert event is not None
    assert event.name == "signup"
    assert event.identity is None
    assert event.is_confirmed is True


@pytest.mark.django_db
def test_record_event_without_identity_logs_anonymous(request_without_identity):
    request_without_identity._allowed_events = {"signup"}

    with patch("django_attribution.querysets.logger") as mock_logger:
        event = Event.objects.record(request_without_identity, "signup")

        assert event is not None
        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args[0][0]
        assert "Recorded event 'signup'" in call_args
        assert "for identity anonymous" in call_args


@pytest.mark.django_db
def test_record_event_logs_successful_creation_with_identity(
    request_with_identity,
):
    request_with_identity._allowed_events = {"purchase"}

    with patch("django_attribution.querysets.logger") as mock_logger:
        event = Event.objects.record(request_with_identity, "purchase")

        assert event is not None
        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args[0][0]
        assert "Recorded event 'purchase'" in call_args
        assert f"for identity {request_with_identity.identity.uuid}" in call_args


@pytest.mark.django_db
def test_record_event_without_allowed_events_constraint(request_with_identity):
    event = Event.objects.record(request_with_identity, "any_event_name")

    assert event is not None
    assert event.name == "any_event_name"
    assert event.identity == request_with_identity.identity


@pytest.mark.django_db
def test_record_event_default_currency_when_not_specified(request_with_identity):
    request_with_identity._allowed_events = {"purchase"}

    event = Event.objects.record(
        request_with_identity, "purchase", monetary_value=50.00
    )

    assert event.currency == "EUR"


@pytest.mark.django_db
def test_record_event_delegates_to_queryset_record(request_with_identity):
    with patch.object(Event.objects, "record") as mock_record:
        mock_record.return_value = Mock()

        result = record_event(request_with_identity, "signup")

        mock_record.assert_called_once_with(request_with_identity, "signup")

        assert result == mock_record.return_value
