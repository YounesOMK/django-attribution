import uuid
from unittest.mock import patch

import pytest
from django.contrib.auth.models import AnonymousUser

from django_attribution.conf import django_attribution_settings
from django_attribution.models import Identity, Touchpoint


@pytest.mark.django_db
def test_new_visitor_cookie_creation_with_utm_parameters(
    attribution_middleware, utm_parameter_middleware, make_request
):
    request = make_request(
        "/landing-page/",
        utm_params={
            "utm_source": "google",
            "utm_medium": "cpc",
            "utm_campaign": "summer_sale",
        },
    )
    request.user = AnonymousUser()

    utm_parameter_middleware(request)

    with patch.object(
        attribution_middleware.tracker, "get_identity_reference", return_value=None
    ):
        response = attribution_middleware(request)

    assert Identity.objects.count() == 1
    assert Touchpoint.objects.count() == 1

    identity = Identity.objects.first()
    assert identity is not None

    cookie_name = django_attribution_settings.COOKIE_NAME
    assert cookie_name in response.cookies

    cookie = response.cookies[cookie_name]

    assert cookie.value == str(identity.uuid)

    uuid.UUID(cookie.value)


@pytest.mark.django_db
def test_new_visitor_cookie_has_correct_name(
    attribution_middleware, utm_parameter_middleware, make_request
):
    request = make_request("/", utm_params={"utm_source": "facebook"})
    request.user = AnonymousUser()

    utm_parameter_middleware(request)

    with patch.object(
        attribution_middleware.tracker, "get_identity_reference", return_value=None
    ):
        response = attribution_middleware(request)

    expected_cookie_name = "_dj_attr_id"
    assert expected_cookie_name in response.cookies
    assert expected_cookie_name == django_attribution_settings.COOKIE_NAME


@pytest.mark.django_db
def test_new_visitor_cookie_has_90_day_expiry(
    attribution_middleware, utm_parameter_middleware, make_request
):
    request = make_request("/", utm_params={"utm_source": "email"})
    request.user = AnonymousUser()

    utm_parameter_middleware(request)

    with patch.object(
        attribution_middleware.tracker, "get_identity_reference", return_value=None
    ):
        response = attribution_middleware(request)

    cookie_name = django_attribution_settings.COOKIE_NAME
    cookie = response.cookies[cookie_name]

    expected_max_age = 60 * 60 * 24 * 90
    assert cookie["max-age"] == expected_max_age
    assert expected_max_age == django_attribution_settings.COOKIE_MAX_AGE


@pytest.mark.django_db
def test_new_visitor_cookie_has_security_attributes(
    attribution_middleware, utm_parameter_middleware, make_request
):
    request = make_request("/", utm_params={"utm_source": "twitter"})
    request.user = AnonymousUser()

    utm_parameter_middleware(request)

    with patch.object(
        attribution_middleware.tracker, "get_identity_reference", return_value=None
    ):
        response = attribution_middleware(request)

    cookie_name = django_attribution_settings.COOKIE_NAME
    cookie = response.cookies[cookie_name]

    assert cookie["httponly"] is True

    assert cookie["samesite"] == "Lax"

    assert cookie["path"] == "/"


@pytest.mark.django_db
def test_new_visitor_cookie_not_set_without_utm_parameters(
    attribution_middleware, utm_parameter_middleware, make_request
):
    request = make_request("/")  # No UTM parameters
    request.user = AnonymousUser()

    utm_parameter_middleware(request)

    with patch.object(
        attribution_middleware.tracker, "get_identity_reference", return_value=None
    ):
        response = attribution_middleware(request)

    assert Identity.objects.count() == 0
    assert Touchpoint.objects.count() == 0

    cookie_name = django_attribution_settings.COOKIE_NAME
    assert cookie_name not in response.cookies


@pytest.mark.django_db
def test_cookie_value_matches_created_identity_uuid(
    attribution_middleware, utm_parameter_middleware, make_request
):
    request = make_request(
        "/signup/",
        utm_params={"utm_source": "instagram", "utm_campaign": "influencer_promo"},
    )
    request.user = AnonymousUser()

    utm_parameter_middleware(request)

    with patch.object(
        attribution_middleware.tracker, "get_identity_reference", return_value=None
    ):
        response = attribution_middleware(request)

    identity = Identity.objects.first()
    assert identity is not None

    cookie_name = django_attribution_settings.COOKIE_NAME
    cookie_value = response.cookies[cookie_name].value

    assert cookie_value == str(identity.uuid)

    parsed_uuid = uuid.UUID(cookie_value)
    assert parsed_uuid.version == 4
    assert str(parsed_uuid) == cookie_value
