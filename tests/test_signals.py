from unittest.mock import patch

import pytest
from django.contrib.auth.signals import user_logged_in

from django_attribution.signals import handle_attribution_on_login


@pytest.fixture
def request_with_tracking_params(make_request):
    request = make_request("/login/")
    request.META["tracking_params"] = {
        "utm_source": "google",
        "utm_medium": "cpc",
        "utm_campaign": "summer_sale",
    }
    return request


@pytest.fixture
def request_without_tracking_params(make_request):
    request = make_request("/login/")
    request.META["tracking_params"] = {}
    return request


@pytest.fixture
def request_no_tracking_meta(make_request):
    request = make_request("/login/")
    return request


@pytest.mark.django_db
def test_signal_handles_login_with_tracking_params(
    request_with_tracking_params, authenticated_user, identity
):
    with patch(
        "django_attribution.signals.reconcile_user_identity"
    ) as mock_reconcile, patch("django_attribution.signals.logger") as mock_logger:
        mock_reconcile.return_value = identity
        handle_attribution_on_login(
            sender=None,
            request=request_with_tracking_params,
            user=authenticated_user,
        )

        mock_reconcile.assert_called_once_with(request_with_tracking_params)

        mock_logger.info.assert_any_call(
            "Handling attribution reconciliation "
            f"for user {authenticated_user.id} login"
        )
        mock_logger.info.assert_any_call(
            f"Successfully reconciled identity for user {authenticated_user.id} "
            f"to canonical identity {identity.uuid}"
        )


@pytest.mark.django_db
def test_signal_handles_login_with_tracking_params_no_canonical_identity(
    request_with_tracking_params, authenticated_user
):
    with patch(
        "django_attribution.signals.reconcile_user_identity"
    ) as mock_reconcile, patch("django_attribution.signals.logger") as mock_logger:
        mock_reconcile.return_value = None
        handle_attribution_on_login(
            sender=None,
            request=request_with_tracking_params,
            user=authenticated_user,
        )

        mock_reconcile.assert_called_once_with(request_with_tracking_params)

        mock_logger.info.assert_any_call(
            "Handling attribution reconciliation for "
            f"user {authenticated_user.id} login"
        )
        mock_logger.info.assert_any_call(
            "No canonical identity found for "
            f"user {authenticated_user.id}, skipping reconciliation"
        )


@pytest.mark.django_db
def test_signal_processes_reconciliation_with_real_tracking_params(
    request_with_tracking_params, authenticated_user, identity
):
    request_with_tracking_params.META["tracking_params"] = {
        "utm_source": "facebook",
        "utm_medium": "social",
        "utm_campaign": "brand_awareness",
        "utm_content": "carousel_ad",
    }

    with patch(
        "django_attribution.signals.reconcile_user_identity"
    ) as mock_reconcile, patch("django_attribution.signals.logger") as mock_logger:
        mock_reconcile.return_value = identity
        handle_attribution_on_login(
            sender=None,
            request=request_with_tracking_params,
            user=authenticated_user,
        )

        mock_reconcile.assert_called_once_with(request_with_tracking_params)

        mock_logger.info.assert_any_call(
            "Successfully reconciled identity for "
            f"user {authenticated_user.id} "
            f"to canonical identity {identity.uuid}"
        )


@pytest.mark.django_db
def test_signal_exits_early_with_empty_tracking_params(
    request_without_tracking_params, authenticated_user
):
    with patch(
        "django_attribution.signals.reconcile_user_identity"
    ) as mock_reconcile, patch("django_attribution.signals.logger") as mock_logger:
        handle_attribution_on_login(
            sender=None,
            request=request_without_tracking_params,
            user=authenticated_user,
        )

        mock_reconcile.assert_not_called()
        mock_logger.info.assert_not_called()
        mock_logger.error.assert_not_called()


@pytest.mark.django_db
def test_signal_exits_early_with_no_tracking_params_key(
    request_no_tracking_meta, authenticated_user
):
    with patch(
        "django_attribution.signals.reconcile_user_identity"
    ) as mock_reconcile, patch("django_attribution.signals.logger") as mock_logger:
        handle_attribution_on_login(
            sender=None, request=request_no_tracking_meta, user=authenticated_user
        )

        mock_reconcile.assert_not_called()
        mock_logger.info.assert_not_called()
        mock_logger.error.assert_not_called()


@pytest.mark.django_db
def test_signal_exits_early_with_none_tracking_params(make_request, authenticated_user):
    request = make_request("/login/")
    request.META["tracking_params"] = None

    with patch(
        "django_attribution.signals.reconcile_user_identity"
    ) as mock_reconcile, patch("django_attribution.signals.logger") as mock_logger:
        handle_attribution_on_login(
            sender=None, request=request, user=authenticated_user
        )

        mock_reconcile.assert_not_called()
        mock_logger.info.assert_not_called()
        mock_logger.error.assert_not_called()


@pytest.mark.django_db
def test_signal_handles_reconciliation_exception_with_logging(
    request_with_tracking_params, authenticated_user
):
    test_exception = ValueError("Test reconciliation error")

    with patch("django_attribution.signals.reconcile_user_identity") as mock_reconcile:
        mock_reconcile.side_effect = test_exception

        with patch("django_attribution.signals.logger") as mock_logger:
            handle_attribution_on_login(
                sender=None,
                request=request_with_tracking_params,
                user=authenticated_user,
            )

            mock_reconcile.assert_called_once_with(request_with_tracking_params)

            mock_logger.info.assert_called_with(
                "Handling attribution reconciliation for "
                f"user {authenticated_user.id} login"
            )

            mock_logger.error.assert_called_once_with(
                "Error during attribution reconciliation for "
                f"user {authenticated_user.id}: {test_exception}",
                exc_info=True,
            )


@pytest.mark.django_db
def test_signal_handles_different_exception_types(
    request_with_tracking_params, authenticated_user
):
    exceptions_to_test = [
        ValueError("Value error in reconciliation"),
        RuntimeError("Runtime error in reconciliation"),
        Exception("Generic exception in reconciliation"),
        AttributeError("Attribute error in reconciliation"),
    ]

    for test_exception in exceptions_to_test:
        with patch(
            "django_attribution.signals.reconcile_user_identity"
        ) as mock_reconcile:
            mock_reconcile.side_effect = test_exception

            with patch("django_attribution.signals.logger") as mock_logger:
                handle_attribution_on_login(
                    sender=None,
                    request=request_with_tracking_params,
                    user=authenticated_user,
                )

                mock_logger.error.assert_called_once_with(
                    "Error during attribution reconciliation for "
                    f"user {authenticated_user.id}: {test_exception}",
                    exc_info=True,
                )


@pytest.mark.django_db
def test_signal_exception_does_not_prevent_other_signal_handlers(
    request_with_tracking_params, authenticated_user
):
    with patch("django_attribution.signals.reconcile_user_identity") as mock_reconcile:
        mock_reconcile.side_effect = Exception("Reconciliation failed")

        try:
            handle_attribution_on_login(
                sender=None,
                request=request_with_tracking_params,
                user=authenticated_user,
            )
        except Exception as e:
            pytest.fail(f"Signal handler raised exception: {e}")


@pytest.mark.django_db
def test_signal_connected_to_user_logged_in():
    connected_receivers = [receiver[1]() for receiver in user_logged_in.receivers]

    assert handle_attribution_on_login in connected_receivers
