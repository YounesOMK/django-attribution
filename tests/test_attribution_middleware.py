from unittest.mock import patch

import pytest
from django.contrib.auth.models import AnonymousUser

from django_attribution.models import Identity, Touchpoint


@pytest.mark.django_db
def test_middleware_creates_identity_and_touchpoint_for_new_visitor_with_utm(
    attribution_middleware, make_request
):
    request = make_request(
        path="/",
        utm_params={
            "utm_source": "google",
            "utm_medium": "cpc",
            "utm_campaign": "test",
        },
    )
    request.user = AnonymousUser()
    request.META["utm_params"] = {
        "utm_source": "google",
        "utm_medium": "cpc",
        "utm_campaign": "test",
    }

    attribution_middleware(request)

    assert Identity.objects.count() == 1
    identity = Identity.objects.first()
    assert identity is not None

    assert Touchpoint.objects.count() == 1
    touchpoint = Touchpoint.objects.first()
    assert touchpoint is not None

    assert touchpoint.identity == identity
    assert touchpoint.utm_source == "google"
    assert touchpoint.utm_medium == "cpc"
    assert touchpoint.utm_campaign == "test"
    assert (
        touchpoint.url
        == "http://testserver/?utm_source=google&utm_medium=cpc&utm_campaign=test"
    )

    assert hasattr(request, "attribution")
    assert request.attribution.identity == identity


@pytest.mark.django_db
def test_middleware_does_not_create_identity_and_touchpoint_for_new_visitor_without_utm(
    make_request, utm_parameter_middleware, attribution_middleware, anonymous_user
):
    request = make_request("/")
    request.user = anonymous_user

    utm_parameter_middleware(request)
    attribution_middleware(request)

    assert Identity.objects.count() == 0
    assert Touchpoint.objects.count() == 0

    # Request should still have attribution manager but with no identity
    assert hasattr(request, "attribution")
    assert request.attribution.identity is None


@pytest.mark.django_db
def test_middleware_finds_existing_identity_for_returning_visitor(
    make_request, attribution_middleware, utm_parameter_middleware, anonymous_user
):
    existing_identity = Identity.objects.create(
        tracking_method=Identity.TrackingMethod.COOKIE
    )

    request = make_request(
        "/", utm_params={"utm_source": "facebook", "utm_medium": "social"}
    )
    request.user = anonymous_user

    utm_parameter_middleware(request)

    with patch.object(
        attribution_middleware.tracker,
        "get_identity_reference",
        return_value=str(existing_identity.uuid),
    ):
        attribution_middleware(request)

    # Should not create a new identity
    assert Identity.objects.count() == 1

    # Should create a new touchpoint for the existing identity
    assert Touchpoint.objects.count() == 1
    touchpoint = Touchpoint.objects.first()
    assert touchpoint is not None
    assert touchpoint.identity == existing_identity
    assert touchpoint.utm_source == "facebook"
    assert touchpoint.utm_medium == "social"

    assert request.attribution.identity == existing_identity


@pytest.mark.django_db
def test_middleware_records_complete_touchpoint_data(
    make_request, utm_parameter_middleware, attribution_middleware, anonymous_user
):
    request = make_request(
        "/test-page/",
        utm_params={
            "utm_source": "google",
            "utm_medium": "cpc",
            "utm_campaign": "brand",
            "utm_term": "keyword",
            "utm_content": "ad1",
        },
    )
    request.user = anonymous_user
    request.META.update(
        {
            "HTTP_REFERER": "https://google.com/search",
            "HTTP_USER_AGENT": "Mozilla/5.0 Test Browser",
            "REMOTE_ADDR": "192.168.1.100",
        }
    )

    utm_parameter_middleware(request)
    attribution_middleware(request)

    assert Touchpoint.objects.count() == 1
    touchpoint = Touchpoint.objects.first()
    assert touchpoint is not None
    assert touchpoint.utm_source == "google"
    assert touchpoint.utm_medium == "cpc"
    assert touchpoint.utm_campaign == "brand"
    assert touchpoint.utm_term == "keyword"
    assert touchpoint.utm_content == "ad1"
    assert touchpoint.referrer == "https://google.com/search"
    assert touchpoint.user_agent == "Mozilla/5.0 Test Browser"
    assert touchpoint.ip_address == "192.168.1.100"
    assert "test-page" in touchpoint.url


@pytest.mark.django_db
def test_middleware_extracts_ip_from_x_forwarded_for(
    make_request, utm_parameter_middleware, attribution_middleware, anonymous_user
):
    request = make_request("/", utm_params={"utm_source": "test"})
    request.user = anonymous_user
    request.META.update(
        {
            "HTTP_X_FORWARDED_FOR": "203.0.113.1, 198.51.100.1, 192.168.1.1",
            "REMOTE_ADDR": "192.168.1.1",
        }
    )

    utm_parameter_middleware(request)
    attribution_middleware(request)

    touchpoint = Touchpoint.objects.first()
    assert touchpoint is not None
    assert touchpoint.ip_address == "203.0.113.1"


@pytest.mark.django_db
def test_middleware_applies_tracker_to_response(
    make_request, utm_parameter_middleware, attribution_middleware, anonymous_user
):
    request = make_request("/", utm_params={"utm_source": "test"})
    request.user = anonymous_user

    utm_parameter_middleware(request)

    with patch.object(
        attribution_middleware.tracker, "apply_to_response"
    ) as mock_apply:
        response = attribution_middleware(request)

        mock_apply.assert_called_once()
        args = mock_apply.call_args[0]
        assert args[0] == request
        assert args[1] == response


@pytest.mark.django_db
def test_middleware_handles_errors_gracefully(
    make_request, utm_parameter_middleware, attribution_middleware, anonymous_user
):
    request = make_request("/", utm_params={"utm_source": "test"})
    request.user = anonymous_user

    utm_parameter_middleware(request)

    with patch.object(
        attribution_middleware, "_resolve_identity", side_effect=Exception("Test error")
    ):
        response = attribution_middleware(request)

        assert response.status_code == 200
        assert response.content == b"OK"

        assert Identity.objects.count() == 0
        assert Touchpoint.objects.count() == 0


@pytest.mark.django_db
def test_middleware_handles_nonexistent_identity_uuid(
    make_request, utm_parameter_middleware, attribution_middleware, anonymous_user
):
    request = make_request("/", utm_params={"utm_source": "test"})
    request.user = anonymous_user

    utm_parameter_middleware(request)

    fake_uuid = "a0b1c2d3-e4f5-6789-abcd-ef0123456789"
    with patch.object(
        attribution_middleware.tracker, "get_identity_reference", return_value=fake_uuid
    ):
        attribution_middleware(request)

    assert Identity.objects.count() == 1
    assert Touchpoint.objects.count() == 1

    new_identity = Identity.objects.first()
    assert new_identity is not None
    assert str(new_identity.uuid) != fake_uuid


@pytest.mark.django_db
def test_middleware_tracks_existing_identity_without_utm_params(
    make_request, utm_parameter_middleware, attribution_middleware, anonymous_user
):
    existing_identity = Identity.objects.create(
        tracking_method=Identity.TrackingMethod.COOKIE
    )

    request = make_request("/some-page/")  # No UTM params
    request.user = anonymous_user

    utm_parameter_middleware(request)

    with patch.object(
        attribution_middleware.tracker,
        "get_identity_reference",
        return_value=str(existing_identity.uuid),
    ):
        attribution_middleware(request)

    assert Identity.objects.count() == 1
    assert Touchpoint.objects.count() == 0


@pytest.mark.django_db
def test_middleware_preserves_utm_params_in_touchpoint(
    make_request, utm_parameter_middleware, attribution_middleware, anonymous_user
):
    request = make_request(
        "/", utm_params={"utm_source": "google", "utm_campaign": "test"}
    )
    request.user = anonymous_user

    utm_parameter_middleware(request)
    attribution_middleware(request)

    touchpoint = Touchpoint.objects.first()
    assert touchpoint is not None
    assert touchpoint.utm_source == "google"
    assert touchpoint.utm_medium == ""
    assert touchpoint.utm_campaign == "test"
    assert touchpoint.utm_term == ""
    assert touchpoint.utm_content == ""


@pytest.mark.django_db
def test_middleware_handles_invalid_utm_params(
    make_request, utm_parameter_middleware, attribution_middleware, anonymous_user
):
    request = make_request(
        "/", utm_params={"utm_source": "valid", "utm_medium": "x" * 1000}
    )  # Too long
    request.user = anonymous_user

    utm_parameter_middleware(request)
    attribution_middleware(request)

    assert Identity.objects.count() == 1
    assert Touchpoint.objects.count() == 1

    touchpoint = Touchpoint.objects.first()
    assert touchpoint is not None
    assert touchpoint.utm_source == "valid"
    assert touchpoint.utm_medium == ""
