from unittest.mock import patch

import pytest
from django.contrib.auth.models import AnonymousUser

from django_attribution.conf import attribution_settings
from django_attribution.models import Conversion, Identity, Touchpoint


@pytest.mark.django_db
def test_new_anonymous_visitor_with_tracking_parameters_creates_identity_and_touchpoint(
    attribution_middleware, tracking_parameter_middleware, make_request
):
    request = make_request(
        "/landing-page/",
        tracking_params={
            "utm_source": "google",
            "utm_medium": "cpc",
            "utm_campaign": "summer_sale",
        },
    )
    request.user = AnonymousUser()

    tracking_parameter_middleware(request)

    with patch.object(
        attribution_middleware.tracker, "get_identity_reference", return_value=None
    ):
        response = attribution_middleware(request)

    assert Identity.objects.count() == 1
    assert Touchpoint.objects.count() == 1

    identity = Identity.objects.first()
    assert identity is not None
    assert identity.linked_user is None  # Anonymous
    assert identity.is_canonical() is True

    touchpoint = Touchpoint.objects.first()
    assert touchpoint is not None
    assert touchpoint.identity == identity
    assert touchpoint.utm_source == "google"
    assert touchpoint.utm_medium == "cpc"
    assert touchpoint.utm_campaign == "summer_sale"
    assert (
        touchpoint.url
        == "http://testserver/landing-page/?utm_source=google&utm_medium=cpc&utm_campaign=summer_sale"
    )

    cookie_name = attribution_settings.COOKIE_NAME
    assert cookie_name in response.cookies
    assert response.cookies[cookie_name].value == str(identity.uuid)


@pytest.mark.django_db
def test_new_anonymous_visitor_without_tracking_parameters_creates_nothing(
    attribution_middleware, tracking_parameter_middleware, make_request
):
    request = make_request("/some-page/")  # No tracking params
    request.user = AnonymousUser()

    tracking_parameter_middleware(request)

    with patch.object(
        attribution_middleware.tracker, "get_identity_reference", return_value=None
    ):
        response = attribution_middleware(request)

    assert Identity.objects.count() == 0
    assert Touchpoint.objects.count() == 0

    cookie_name = attribution_settings.COOKIE_NAME
    assert cookie_name not in response.cookies


@pytest.mark.django_db
def test_new_anon_visitor_with_attribution_header_creates_identity_without_touchpoint(
    attribution_middleware, tracking_parameter_middleware, make_request
):
    request = make_request("/api-endpoint/")
    request.user = AnonymousUser()

    request.META[attribution_settings.ATTRIBUTION_TRIGGER_HEADER] = "any_value"

    tracking_parameter_middleware(request)

    with patch.object(
        attribution_middleware.tracker, "get_identity_reference", return_value=None
    ):
        response = attribution_middleware(request)

    assert Identity.objects.count() == 1
    assert Touchpoint.objects.count() == 0  # No touchpoint without UTM data

    identity = Identity.objects.first()
    assert identity is not None
    assert identity.linked_user is None  # Anonymous
    assert identity.is_canonical() is True

    cookie_name = attribution_settings.COOKIE_NAME
    assert cookie_name in response.cookies
    assert response.cookies[cookie_name].value == str(identity.uuid)


@pytest.mark.django_db
def test_anonymous_user_with_existing_identity_logs_in_links_identity_to_account(
    attribution_middleware,
    tracking_parameter_middleware,
    make_request,
    authenticated_user,
):
    existing_identity = Identity.objects.create(
        first_visit_user_agent="Mozilla/5.0...", linked_user=None
    )

    Touchpoint.objects.create(
        identity=existing_identity,
        url="https://site.com/landing",
        utm_source="facebook",
        utm_campaign="brand_awareness",
    )
    Touchpoint.objects.create(
        identity=existing_identity,
        url="https://site.com/products",
        utm_source="google",
        utm_campaign="product_search",
    )

    request = make_request("/login-success/")
    request.user = authenticated_user

    tracking_parameter_middleware(request)

    with patch.object(
        attribution_middleware.tracker,
        "get_identity_reference",
        return_value=str(existing_identity.uuid),
    ):
        response = attribution_middleware(request)

    assert Identity.objects.count() == 1

    existing_identity.refresh_from_db()
    assert existing_identity.linked_user == authenticated_user
    assert existing_identity.is_canonical() is True

    assert existing_identity.touchpoints.count() == 2
    assert existing_identity.touchpoints.filter(utm_source="facebook").exists()
    assert existing_identity.touchpoints.filter(utm_source="google").exists()

    cookie_name = attribution_middleware.tracker.cookie_name
    assert cookie_name in response.cookies


@pytest.mark.django_db
def test_user_logs_in_on_new_device_with_utm_creates_new_identity_for_user(
    attribution_middleware,
    tracking_parameter_middleware,
    make_request,
    authenticated_user,
):
    request = make_request(
        "/welcome/",
        tracking_params={"utm_source": "email", "utm_campaign": "welcome_back"},
    )
    request.user = authenticated_user

    tracking_parameter_middleware(request)

    with patch.object(
        attribution_middleware.tracker, "get_identity_reference", return_value=None
    ):
        response = attribution_middleware(request)

    assert Identity.objects.count() == 1
    assert Touchpoint.objects.count() == 1

    identity = Identity.objects.first()
    assert identity is not None
    assert identity.linked_user == authenticated_user
    assert identity.is_canonical() is True

    touchpoint = Touchpoint.objects.first()
    assert touchpoint is not None
    assert touchpoint.identity == identity
    assert touchpoint.utm_source == "email"
    assert touchpoint.utm_campaign == "welcome_back"

    cookie_name = attribution_middleware.tracker.cookie_name
    assert cookie_name in response.cookies
    assert response.cookies[cookie_name].value == str(identity.uuid)


@pytest.mark.django_db
def test_merge_identities_on_login_with_anonymous_identity(
    attribution_middleware,
    tracking_parameter_middleware,
    make_request,
    authenticated_user,
):
    canonical_identity = Identity.objects.create(
        linked_user=authenticated_user,
        first_visit_user_agent="Previous Device",
    )

    Touchpoint.objects.create(
        identity=canonical_identity,
        url="https://site.com/old-visit",
        utm_source="email",
        utm_campaign="newsletter",
    )

    anonymous_identity = Identity.objects.create(
        linked_user=None,  # Anonymous
        first_visit_user_agent="New Device",
    )

    Touchpoint.objects.create(
        identity=anonymous_identity,
        url="https://site.com/new-visit",
        utm_source="instagram",
        utm_campaign="social_promo",
    )
    Touchpoint.objects.create(
        identity=anonymous_identity,
        url="https://site.com/checkout",
        utm_source="instagram",
        utm_campaign="social_promo",
    )

    request = make_request("/login-success/")
    request.user = authenticated_user

    tracking_parameter_middleware(request)

    with patch.object(
        attribution_middleware.tracker,
        "get_identity_reference",
        return_value=str(anonymous_identity.uuid),
    ):
        response = attribution_middleware(request)

    assert Identity.objects.count() == 2

    canonical_identity.refresh_from_db()
    assert canonical_identity.linked_user == authenticated_user
    assert canonical_identity.is_canonical() is True

    anonymous_identity.refresh_from_db()
    assert anonymous_identity.is_merged() is True
    assert anonymous_identity.merged_into == canonical_identity
    assert anonymous_identity.linked_user == authenticated_user  # Updated during merge

    assert canonical_identity.touchpoints.count() == 3  # 1 original + 2 transferred
    assert canonical_identity.touchpoints.filter(
        utm_source="email"
    ).exists()  # Original
    assert (
        canonical_identity.touchpoints.filter(utm_source="instagram").count() == 2
    )  # Transferred

    assert anonymous_identity.touchpoints.count() == 0

    cookie_name = attribution_middleware.tracker.cookie_name
    assert cookie_name in response.cookies
    assert response.cookies[cookie_name].value == str(canonical_identity.uuid)


@pytest.mark.django_db
def test_returning_visitor_with_new_utm(
    attribution_middleware, tracking_parameter_middleware, make_request
):
    existing_identity = Identity.objects.create(
        first_visit_user_agent="Mozilla/5.0...",
        linked_user=None,  # Anonymous
    )

    Touchpoint.objects.create(
        identity=existing_identity,
        url="https://site.com/landing",
        utm_source="google",
        utm_campaign="summer_sale",
    )

    request = make_request(
        "/products/",
        tracking_params={
            "utm_source": "facebook",
            "utm_medium": "social",
            "utm_campaign": "autumn_promo",
        },
    )
    request.user = AnonymousUser()

    tracking_parameter_middleware(request)

    with patch.object(
        attribution_middleware.tracker,
        "get_identity_reference",
        return_value=str(existing_identity.uuid),
    ):
        response = attribution_middleware(request)

    assert Identity.objects.count() == 1

    assert Touchpoint.objects.count() == 2

    existing_identity.refresh_from_db()
    assert existing_identity.touchpoints.count() == 2

    new_touchpoint = Touchpoint.objects.exclude(utm_source="google").first()
    assert new_touchpoint is not None
    assert new_touchpoint.identity == existing_identity
    assert new_touchpoint.utm_source == "facebook"
    assert new_touchpoint.utm_medium == "social"
    assert new_touchpoint.utm_campaign == "autumn_promo"
    assert (
        new_touchpoint.url
        == "http://testserver/products/?utm_source=facebook&utm_medium=social&utm_campaign=autumn_promo"
    )

    cookie_name = attribution_middleware.tracker.cookie_name
    assert cookie_name in response.cookies
    assert response.cookies[cookie_name].value == str(existing_identity.uuid)


@pytest.mark.django_db
def test_returning_visitor_with_valid_cookie_no_utm_reuses_identity_no_touchpoint(
    attribution_middleware, tracking_parameter_middleware, make_request
):
    existing_identity = Identity.objects.create(
        first_visit_user_agent="Mozilla/5.0...",
        linked_user=None,  # Anonymous
    )

    Touchpoint.objects.create(
        identity=existing_identity,
        url="https://site.com/landing",
        utm_source="email",
        utm_campaign="newsletter",
    )

    request = make_request("/account/")  # No tracking params
    request.user = AnonymousUser()

    tracking_parameter_middleware(request)

    with patch.object(
        attribution_middleware.tracker,
        "get_identity_reference",
        return_value=str(existing_identity.uuid),
    ):
        response = attribution_middleware(request)

    assert Identity.objects.count() == 1

    assert Touchpoint.objects.count() == 1

    existing_identity.refresh_from_db()
    assert existing_identity.touchpoints.count() == 1

    original_touchpoint = Touchpoint.objects.first()
    assert original_touchpoint is not None
    assert original_touchpoint.identity == existing_identity
    assert original_touchpoint.utm_source == "email"
    assert original_touchpoint.utm_campaign == "newsletter"

    cookie_name = attribution_middleware.tracker.cookie_name
    assert cookie_name in response.cookies
    assert response.cookies[cookie_name].value == str(existing_identity.uuid)


@pytest.mark.django_db
def test_returning_visitor_with_corrupted_cookie_creates_fresh_identity(
    attribution_middleware, tracking_parameter_middleware, make_request
):
    old_identity = Identity.objects.create(
        first_visit_user_agent="Old Browser", linked_user=None
    )

    request = make_request(
        "/special-offer/",
        tracking_params={
            "utm_source": "twitter",
            "utm_medium": "social",
            "utm_campaign": "flash_sale",
        },
    )
    request.user = AnonymousUser()

    tracking_parameter_middleware(request)

    with patch.object(
        attribution_middleware, "_get_current_identity_from_cookie", return_value=None
    ):
        response = attribution_middleware(request)

    assert Identity.objects.count() == 2
    assert Touchpoint.objects.count() == 1

    new_identity = Identity.objects.exclude(id=old_identity.id).first()
    assert new_identity is not None
    assert new_identity.linked_user is None  # Anonymous
    assert new_identity.is_canonical() is True

    touchpoint = Touchpoint.objects.first()
    assert touchpoint is not None
    assert touchpoint.identity == new_identity
    assert touchpoint.utm_source == "twitter"
    assert touchpoint.utm_medium == "social"
    assert touchpoint.utm_campaign == "flash_sale"
    assert (
        touchpoint.url
        == "http://testserver/special-offer/?utm_source=twitter&utm_medium=social&utm_campaign=flash_sale"
    )

    cookie_name = attribution_middleware.tracker.cookie_name
    assert cookie_name in response.cookies
    assert response.cookies[cookie_name].value == str(new_identity.uuid)
    assert response.cookies[cookie_name].value != str(old_identity.uuid)


@pytest.mark.django_db
def test_user_with_multiple_identities_consolidates_to_canonical_identity(
    attribution_middleware,
    tracking_parameter_middleware,
    make_request,
    authenticated_user,
):
    canonical_identity = Identity.objects.create(
        linked_user=authenticated_user,
        first_visit_user_agent="Previous Device",
    )

    anonymous_identity = Identity.objects.create(
        linked_user=None,  # Anonymous browsing
        first_visit_user_agent="New Device",
    )

    old_merged_identity = Identity.objects.create(
        linked_user=authenticated_user,
        merged_into=canonical_identity,
    )

    request = make_request("/welcome-back/")
    request.user = authenticated_user

    tracking_parameter_middleware(request)

    with patch.object(
        attribution_middleware.tracker,
        "get_identity_reference",
        return_value=str(anonymous_identity.uuid),
    ):
        response = attribution_middleware(request)

    assert Identity.objects.count() == 3

    canonical_identity.refresh_from_db()
    assert canonical_identity.is_canonical() is True
    assert canonical_identity.linked_user == authenticated_user

    anonymous_identity.refresh_from_db()
    assert anonymous_identity.is_merged() is True
    assert anonymous_identity.merged_into == canonical_identity
    assert anonymous_identity.linked_user == authenticated_user  # Updated during merge

    old_merged_identity.refresh_from_db()
    assert old_merged_identity.is_merged() is True
    assert old_merged_identity.merged_into == canonical_identity

    cookie_name = attribution_middleware.tracker.cookie_name
    assert cookie_name in response.cookies
    assert response.cookies[cookie_name].value == str(canonical_identity.uuid)


@pytest.mark.django_db
def test_touchpoints_and_conversions_transfer_to_canonical_identity_during_merge(
    attribution_middleware,
    tracking_parameter_middleware,
    make_request,
    authenticated_user,
):
    canonical_identity = Identity.objects.create(linked_user=authenticated_user)

    Touchpoint.objects.create(
        identity=canonical_identity,
        url="https://site.com/old-visit",
        utm_source="email",
        utm_campaign="newsletter",
    )

    Conversion.objects.create(
        identity=canonical_identity, event="signup", conversion_value=0
    )

    anonymous_identity = Identity.objects.create(linked_user=None)

    Touchpoint.objects.create(
        identity=anonymous_identity,
        url="https://site.com/landing",
        utm_source="facebook",
        utm_campaign="social_promo",
    )
    Touchpoint.objects.create(
        identity=anonymous_identity,
        url="https://site.com/products",
        utm_source="facebook",
        utm_campaign="social_promo",
    )

    Conversion.objects.create(
        identity=anonymous_identity, event="purchase", conversion_value=99.99
    )

    request = make_request("/dashboard/")
    request.user = authenticated_user

    tracking_parameter_middleware(request)

    with patch.object(
        attribution_middleware.tracker,
        "get_identity_reference",
        return_value=str(anonymous_identity.uuid),
    ):
        attribution_middleware(request)

    canonical_identity.refresh_from_db()
    assert canonical_identity.touchpoints.count() == 3
    assert canonical_identity.touchpoints.filter(
        utm_source="email"
    ).exists()  # Original
    assert (
        canonical_identity.touchpoints.filter(utm_source="facebook").count() == 2
    )  # Transferred

    assert canonical_identity.conversions.count() == 2
    assert canonical_identity.conversions.filter(event="signup").exists()  # Original
    assert canonical_identity.conversions.filter(
        event="purchase"
    ).exists()  # Transferred

    anonymous_identity.refresh_from_db()
    assert anonymous_identity.touchpoints.count() == 0
    assert anonymous_identity.conversions.count() == 0
    assert anonymous_identity.is_merged() is True

    purchase_conversion = canonical_identity.conversions.filter(
        event="purchase"
    ).first()
    assert purchase_conversion is not None
    assert float(purchase_conversion.conversion_value) == 99.99

    facebook_touchpoints = canonical_identity.touchpoints.filter(utm_source="facebook")
    assert facebook_touchpoints.count() == 2
    assert facebook_touchpoints.filter(url__contains="landing").exists()
    assert facebook_touchpoints.filter(url__contains="products").exists()


@pytest.mark.django_db
def test_cookie_updates_to_canonical_identity_uuid_after_reconciliation(
    attribution_middleware,
    tracking_parameter_middleware,
    make_request,
    authenticated_user,
):
    canonical_identity = Identity.objects.create(
        linked_user=authenticated_user, first_visit_user_agent="Desktop"
    )

    anonymous_identity = Identity.objects.create(
        linked_user=None, first_visit_user_agent="Mobile"
    )

    canonical_uuid = str(canonical_identity.uuid)
    anonymous_uuid = str(anonymous_identity.uuid)

    request = make_request("/login-success/")
    request.user = authenticated_user

    tracking_parameter_middleware(request)

    with patch.object(
        attribution_middleware.tracker,
        "get_identity_reference",
        return_value=anonymous_uuid,
    ):
        response = attribution_middleware(request)

    cookie_name = attribution_middleware.tracker.cookie_name
    assert cookie_name in response.cookies
    assert response.cookies[cookie_name].value == canonical_uuid
    assert response.cookies[cookie_name].value != anonymous_uuid

    anonymous_identity.refresh_from_db()
    assert anonymous_identity.is_merged() is True
    assert anonymous_identity.merged_into == canonical_identity

    canonical_identity.refresh_from_db()
    assert canonical_identity.is_canonical() is True
    assert canonical_identity.uuid.hex == canonical_uuid.replace("-", "")


@pytest.mark.django_db
def test_user_with_no_existing_canonical_identity_promotes_anonymous_to_canonical(
    attribution_middleware,
    tracking_parameter_middleware,
    make_request,
    authenticated_user,
):
    anonymous_identity = Identity.objects.create(
        linked_user=None, first_visit_user_agent="Chrome"
    )

    Touchpoint.objects.create(
        identity=anonymous_identity,
        url="https://site.com/signup",
        utm_source="google",
        utm_campaign="brand_search",
    )

    request = make_request("/onboarding/")
    request.user = authenticated_user

    tracking_parameter_middleware(request)

    with patch.object(
        attribution_middleware.tracker,
        "get_identity_reference",
        return_value=str(anonymous_identity.uuid),
    ):
        response = attribution_middleware(request)

    assert Identity.objects.count() == 1

    anonymous_identity.refresh_from_db()
    assert anonymous_identity.linked_user == authenticated_user
    assert anonymous_identity.is_canonical() is True
    assert anonymous_identity.is_merged() is False

    assert anonymous_identity.touchpoints.count() == 1
    touchpoint = anonymous_identity.touchpoints.first()
    assert touchpoint is not None
    assert touchpoint.utm_source == "google"
    assert touchpoint.utm_campaign == "brand_search"

    cookie_name = attribution_middleware.tracker.cookie_name
    assert cookie_name in response.cookies
    assert response.cookies[cookie_name].value == str(anonymous_identity.uuid)


@pytest.mark.django_db
def test_excluded_url_patterns_skip_attribution_logic(
    attribution_middleware, tracking_parameter_middleware, make_request
):
    excluded_urls = [
        "/admin/",
        "/admin/login/",
        "/admin/users/add/",
        "/api/",
        "/api/v1/health/",
        "/api/v2/metrics/",
    ]

    for url in excluded_urls:
        request = make_request(
            url,
            tracking_params={
                "utm_source": "facebook",
                "utm_medium": "social",
                "utm_campaign": "excluded_test",
            },
        )
        request.user = AnonymousUser()
        request.META["HTTP_USER_AGENT"] = "Mozilla/5.0 (regular user agent)"

        tracking_parameter_middleware(request)

        # Mock no existing cookie
        with patch.object(
            attribution_middleware.tracker, "get_identity_reference", return_value=None
        ):
            response = attribution_middleware(request)

        assert (
            request.META.get("tracking_params", {}) == {}
        ), f"Excluded URL should not extract tracking params: {url}"

        assert (
            Identity.objects.count() == 0
        ), f"No identity should be created for excluded URL: {url}"
        assert (
            Touchpoint.objects.count() == 0
        ), f"No touchpoint should be created for excluded URL: {url}"

        cookie_name = attribution_settings.COOKIE_NAME
        assert (
            cookie_name not in response.cookies
        ), f"No cookie should be set for excluded URL: {url}"


@pytest.mark.django_db
def test_bot_filtering_can_be_disabled_via_settings(
    attribution_middleware, tracking_parameter_middleware, make_request
):
    with patch.object(attribution_settings, "FILTER_BOTS", False):
        request = make_request(
            "/landing/",
            tracking_params={"utm_source": "google", "utm_campaign": "bot_test"},
        )
        request.user = AnonymousUser()
        request.META[
            "HTTP_USER_AGENT"
        ] = "Googlebot/2.1 (+http://www.google.com/bot.html)"

        tracking_parameter_middleware(request)

        with patch.object(
            attribution_middleware.tracker, "get_identity_reference", return_value=None
        ):
            response = attribution_middleware(request)

        expected_params = {"utm_source": "google", "utm_campaign": "bot_test"}
        assert request.META.get("tracking_params", {}) == expected_params

        assert Identity.objects.count() == 1
        assert Touchpoint.objects.count() == 1

        cookie_name = attribution_settings.COOKIE_NAME
        assert cookie_name in response.cookies
