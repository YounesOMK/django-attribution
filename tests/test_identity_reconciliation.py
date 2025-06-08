from unittest.mock import patch

import pytest
from django.contrib.auth.models import AnonymousUser, User

from django_attribution.models import Identity, Touchpoint


@pytest.mark.django_db
def test_attribution_identity_resolution_and_user_linking_flow(
    attribution_middleware, utm_parameter_middleware, make_request
):
    user = User.objects.create_user(username="testuser", password="testpass")

    request1 = make_request(
        "/landing",
        utm_params={
            "utm_source": "google",
            "utm_medium": "cpc",
            "utm_campaign": "summer_sale",
        },
    )
    request1.user = AnonymousUser()

    utm_parameter_middleware(request1)

    with patch.object(  # noqa: SIM117
        attribution_middleware.tracker, "get_identity_reference", return_value=None
    ):
        with patch.object(
            attribution_middleware.tracker, "set_identity_reference"
        ) as mock_set_cookie:
            attribution_middleware(request1)

    assert Identity.objects.count() == 1
    assert Touchpoint.objects.count() == 1

    identity1 = Identity.objects.first()
    assert identity1.linked_user is None  # Not linked to user yet

    touchpoint1 = Touchpoint.objects.first()
    assert touchpoint1.identity == identity1
    assert touchpoint1.utm_source == "google"
    assert touchpoint1.utm_campaign == "summer_sale"
    assert "/landing" in touchpoint1.url

    mock_set_cookie.assert_called_once()
    cookie_call = mock_set_cookie.call_args[0]
    assert cookie_call[1] == identity1

    request2 = make_request("/products")
    request2.user = AnonymousUser()

    utm_parameter_middleware(request2)  # No UTM params this time

    with patch.object(
        attribution_middleware.tracker,
        "get_identity_reference",
        return_value=str(identity1.uuid),
    ):
        attribution_middleware(request2)

    assert Identity.objects.count() == 1
    assert Touchpoint.objects.count() == 1  # No new touchpoint without UTM

    assert request2.attribution.identity == identity1

    request3 = make_request(
        "/special-offer",
        utm_params={
            "utm_source": "facebook",
            "utm_medium": "social",
            "utm_campaign": "flash_sale",
        },
    )
    request3.user = AnonymousUser()

    utm_parameter_middleware(request3)

    with patch.object(
        attribution_middleware.tracker,
        "get_identity_reference",
        return_value=str(identity1.uuid),
    ):
        attribution_middleware(request3)

    assert Identity.objects.count() == 1
    assert Touchpoint.objects.count() == 2

    touchpoint2 = Touchpoint.objects.latest("created_at")
    assert touchpoint2.identity == identity1
    assert touchpoint2.utm_source == "facebook"
    assert touchpoint2.utm_campaign == "flash_sale"
    assert "/special-offer" in touchpoint2.url

    request4 = make_request("/login")
    request4.user = user  # Now authenticated

    utm_parameter_middleware(request4)

    with patch.object(  # noqa: SIM117
        attribution_middleware.tracker,
        "get_identity_reference",
        return_value=str(identity1.uuid),
    ):
        with patch.object(attribution_middleware.tracker, "set_identity_reference"):
            attribution_middleware(request4)

    identity1.refresh_from_db()
    assert identity1.linked_user == user
    assert Identity.objects.count() == 1
    assert Touchpoint.objects.count() == 2

    assert request4.attribution.identity == identity1

    request5 = make_request(
        "/dashboard", utm_params={"utm_source": "email", "utm_medium": "newsletter"}
    )
    request5.user = user

    utm_parameter_middleware(request5)

    with patch.object(
        attribution_middleware.tracker,
        "get_identity_reference",
        return_value=str(identity1.uuid),
    ):
        attribution_middleware(request5)

    assert request5.attribution.identity == identity1
    assert Identity.objects.count() == 1
    assert Touchpoint.objects.count() == 3  # New touchpoint for new UTM

    touchpoint3 = Touchpoint.objects.latest("created_at")
    assert touchpoint3.identity == identity1
    assert touchpoint3.utm_source == "email"

    request6 = make_request("/public-page")
    request6.user = AnonymousUser()  # Logged out

    utm_parameter_middleware(request6)

    with patch.object(
        attribution_middleware.tracker,
        "get_identity_reference",
        return_value=str(identity1.uuid),
    ):
        attribution_middleware(request6)

    assert request6.attribution.identity == identity1
    identity1.refresh_from_db()
    assert identity1.linked_user == user  # Still linked to user
    assert Identity.objects.count() == 1
    assert Touchpoint.objects.count() == 3  # No new touchpoint (no UTM)

    final_identity = Identity.objects.first()
    assert final_identity.linked_user == user
    assert final_identity.touchpoints.count() == 3

    touchpoints = list(final_identity.touchpoints.order_by("created_at"))

    assert touchpoints[0].utm_source == "google"
    assert touchpoints[0].utm_campaign == "summer_sale"

    assert touchpoints[1].utm_source == "facebook"
    assert touchpoints[1].utm_campaign == "flash_sale"

    assert touchpoints[2].utm_source == "email"
    assert touchpoints[2].utm_medium == "newsletter"


@pytest.mark.django_db
def test_complex_identity_reconciliation_preserves_attribution_history(
    attribution_middleware, utm_parameter_middleware, make_request
):
    user = User.objects.create_user(username="customer", password="password123")

    browser1_identity = Identity.objects.create()

    Touchpoint.objects.create(
        identity=browser1_identity,
        url="https://site.com/landing?utm_source=google&utm_medium=cpc&utm_campaign=brand",
        utm_source="google",
        utm_medium="cpc",
        utm_campaign="brand",
        referrer="https://google.com/search",
    )

    Touchpoint.objects.create(
        identity=browser1_identity,
        url="https://site.com/products",
        utm_source="",  # Direct navigation
        utm_medium="",
        utm_campaign="",
        referrer="https://site.com/landing",
    )

    browser2_identity = Identity.objects.create()

    Touchpoint.objects.create(
        identity=browser2_identity,
        url="https://site.com/mobile?utm_source=facebook&utm_medium=social&utm_campaign=retargeting",
        utm_source="facebook",
        utm_medium="social",
        utm_campaign="retargeting",
        referrer="https://m.facebook.com",
    )

    Touchpoint.objects.create(
        identity=browser2_identity,
        url="https://site.com/mobile/cart",
        utm_source="",
        utm_medium="",
        utm_campaign="",
        referrer="https://site.com/mobile",
    )

    browser3_identity = Identity.objects.create()

    Touchpoint.objects.create(
        identity=browser3_identity,
        url="https://site.com/newsletter-offer?utm_source=email&utm_medium=newsletter&utm_campaign=weekly",
        utm_source="email",
        utm_medium="newsletter",
        utm_campaign="weekly",
        referrer="https://mailchimp.com",
    )

    assert Identity.objects.count() == 3
    assert Touchpoint.objects.count() == 5
    assert browser1_identity.touchpoints.count() == 2
    assert browser2_identity.touchpoints.count() == 2
    assert browser3_identity.touchpoints.count() == 1

    login_request = make_request("/login")
    login_request.user = user

    with patch.object(  # noqa: SIM117
        attribution_middleware.tracker,
        "get_identity_reference",
        return_value=str(browser1_identity.uuid),
    ):
        with patch.object(attribution_middleware.tracker, "set_identity_reference"):
            attribution_middleware(login_request)

    browser1_identity.refresh_from_db()
    assert browser1_identity.linked_user == user
    assert login_request.attribution.identity == browser1_identity

    browser2_identity.refresh_from_db()
    browser3_identity.refresh_from_db()
    assert browser2_identity.linked_user is None
    assert browser3_identity.linked_user is None

    login_request2 = make_request("/login-mobile")
    login_request2.user = user

    utm_parameter_middleware(login_request2)

    with patch.object(  # noqa: SIM117
        attribution_middleware.tracker,
        "get_identity_reference",
        return_value=str(browser2_identity.uuid),
    ):
        with patch.object(attribution_middleware.tracker, "delete_cookie"):
            with patch.object(
                attribution_middleware.tracker, "set_identity_reference"
            ) as mock_set_cookie:
                attribution_middleware(login_request2)

    browser1_identity.refresh_from_db()
    browser2_identity.refresh_from_db()

    assert browser2_identity.merged_into == browser1_identity
    assert browser2_identity.linked_user == user

    assert browser1_identity.touchpoints.count() == 4  # 2 original + 2 from browser2
    assert browser2_identity.touchpoints.count() == 0  # Moved to canonical

    assert login_request2.attribution.identity == browser1_identity

    mock_set_cookie.assert_called_once()
    cookie_call_args = mock_set_cookie.call_args[0]
    assert cookie_call_args[1] == browser1_identity

    login_request3 = make_request("/login-work")
    login_request3.user = user

    utm_parameter_middleware(login_request3)

    with patch.object(  # noqa: SIM117
        attribution_middleware.tracker,
        "get_identity_reference",
        return_value=str(browser3_identity.uuid),
    ):
        with patch.object(attribution_middleware.tracker, "set_identity_reference"):
            attribution_middleware(login_request3)

    browser1_identity.refresh_from_db()
    browser2_identity.refresh_from_db()
    browser3_identity.refresh_from_db()

    assert browser1_identity.linked_user == user
    assert browser2_identity.linked_user == user
    assert browser3_identity.linked_user == user

    assert browser2_identity.merged_into == browser1_identity
    assert browser3_identity.merged_into == browser1_identity

    canonical_touchpoints = browser1_identity.touchpoints.all().order_by("created_at")
    assert canonical_touchpoints.count() == 5

    touchpoint_sources = [tp.utm_source for tp in canonical_touchpoints]
    touchpoint_campaigns = [tp.utm_campaign for tp in canonical_touchpoints]

    assert "google" in touchpoint_sources
    assert "facebook" in touchpoint_sources
    assert "email" in touchpoint_sources
    assert "brand" in touchpoint_campaigns
    assert "retargeting" in touchpoint_campaigns
    assert "weekly" in touchpoint_campaigns

    touchpoint_urls = [tp.url for tp in canonical_touchpoints]
    assert any("landing" in url for url in touchpoint_urls)
    assert any("mobile" in url for url in touchpoint_urls)
    assert any("newsletter-offer" in url for url in touchpoint_urls)

    assert Identity.objects.count() == 3

    canonical_identities = Identity.objects.filter(
        merged_into__isnull=True, linked_user=user
    )
    assert canonical_identities.count() == 1
    assert canonical_identities.first() == browser1_identity

    assert Touchpoint.objects.filter(identity=browser1_identity).count() == 5
    assert Touchpoint.objects.filter(identity=browser2_identity).count() == 0
    assert Touchpoint.objects.filter(identity=browser3_identity).count() == 0

    assert browser1_identity.get_canonical_identity() == browser1_identity
    assert browser2_identity.get_canonical_identity() == browser1_identity
    assert browser3_identity.get_canonical_identity() == browser1_identity

    continued_request = make_request(
        "/checkout", utm_params={"utm_source": "direct", "utm_medium": "bookmark"}
    )
    continued_request.user = user

    utm_parameter_middleware(continued_request)

    with patch.object(
        attribution_middleware.tracker,
        "get_identity_reference",
        return_value=str(browser2_identity.uuid),
    ):
        attribution_middleware(continued_request)

    assert continued_request.attribution.identity == browser1_identity
    assert browser1_identity.touchpoints.count() == 6

    final_touchpoint = Touchpoint.objects.latest("created_at")
    assert final_touchpoint.identity == browser1_identity
    assert final_touchpoint.utm_source == "direct"


@pytest.mark.django_db
def test_touchpoint_migration_during_identity_merge(
    attribution_middleware, utm_parameter_middleware, make_request
):
    user = User.objects.create_user(username="merger_user", password="pass123")

    canonical_identity = Identity.objects.create(linked_user=user)

    source_identity = Identity.objects.create()

    canonical_tp1 = Touchpoint.objects.create(
        identity=canonical_identity,
        url="https://site.com/home?utm_source=google&utm_medium=cpc",
        utm_source="google",
        utm_medium="cpc",
        utm_campaign="brand_search",
        utm_term="company name",
        utm_content="ad_variant_a",
        referrer="https://google.com/search",
        ip_address="192.168.1.100",
        user_agent="Mozilla/5.0 (Desktop Chrome)",
    )

    canonical_tp2 = Touchpoint.objects.create(
        identity=canonical_identity,
        url="https://site.com/products",
        utm_source="",
        utm_medium="",
        utm_campaign="",
        referrer="https://site.com/home",
        ip_address="192.168.1.100",
        user_agent="Mozilla/5.0 (Desktop Chrome)",
    )

    source_tp1 = Touchpoint.objects.create(
        identity=source_identity,
        url="https://site.com/landing?utm_source=facebook&utm_medium=social",
        utm_source="facebook",
        utm_medium="social",
        utm_campaign="retargeting_q4",
        utm_term="interested_users",
        utm_content="video_ad_30s",
        referrer="https://facebook.com/feed",
        ip_address="10.0.0.50",
        user_agent="Mozilla/5.0 (Mobile Safari)",
    )

    source_tp2 = Touchpoint.objects.create(
        identity=source_identity,
        url="https://site.com/pricing?utm_source=email&utm_medium=newsletter",
        utm_source="email",
        utm_medium="newsletter",
        utm_campaign="weekly_digest",
        utm_term="pricing_focus",
        utm_content="header_cta",
        referrer="https://mailchimp.com",
        ip_address="10.0.0.50",
        user_agent="Mozilla/5.0 (Mobile Safari)",
    )

    source_tp3 = Touchpoint.objects.create(
        identity=source_identity,
        url="https://site.com/signup",
        utm_source="",
        utm_medium="",
        utm_campaign="",
        referrer="https://site.com/pricing",
        ip_address="10.0.0.50",
        user_agent="Mozilla/5.0 (Mobile Safari)",
    )

    assert canonical_identity.touchpoints.count() == 2
    assert source_identity.touchpoints.count() == 3
    assert Touchpoint.objects.count() == 5

    original_canonical_touchpoints = list(
        canonical_identity.touchpoints.values(
            "id",
            "url",
            "utm_source",
            "utm_campaign",
            "referrer",
            "ip_address",
            "created_at",
        )
    )
    original_source_touchpoints = list(
        source_identity.touchpoints.values(
            "id",
            "url",
            "utm_source",
            "utm_campaign",
            "referrer",
            "ip_address",
            "created_at",
        )
    )

    merge_request = make_request("/login-second-device")
    merge_request.user = user

    utm_parameter_middleware(merge_request)

    with patch.object(  # noqa: SIM117
        attribution_middleware.tracker,
        "get_identity_reference",
        return_value=str(source_identity.uuid),
    ):
        with patch.object(attribution_middleware.tracker, "set_identity_reference"):
            attribution_middleware(merge_request)

    canonical_identity.refresh_from_db()
    source_identity.refresh_from_db()

    assert source_identity.merged_into == canonical_identity
    assert source_identity.linked_user == user

    assert canonical_identity.touchpoints.count() == 5
    assert source_identity.touchpoints.count() == 0

    assert Touchpoint.objects.count() == 5

    merged_touchpoints = canonical_identity.touchpoints.all().order_by("created_at")

    touchpoint_ids = [tp.id for tp in merged_touchpoints]

    expected_ids = [
        canonical_tp1.id,
        canonical_tp2.id,
        source_tp1.id,
        source_tp2.id,
        source_tp3.id,
    ]
    assert set(touchpoint_ids) == set(expected_ids)

    facebook_touchpoint = canonical_identity.touchpoints.filter(
        utm_source="facebook"
    ).first()
    assert facebook_touchpoint is not None
    assert facebook_touchpoint.utm_campaign == "retargeting_q4"
    assert facebook_touchpoint.utm_content == "video_ad_30s"
    assert facebook_touchpoint.referrer == "https://facebook.com/feed"
    assert facebook_touchpoint.ip_address == "10.0.0.50"
    assert facebook_touchpoint.user_agent == "Mozilla/5.0 (Mobile Safari)"

    email_touchpoint = canonical_identity.touchpoints.filter(utm_source="email").first()
    assert email_touchpoint is not None
    assert email_touchpoint.utm_campaign == "weekly_digest"
    assert email_touchpoint.utm_term == "pricing_focus"
    assert email_touchpoint.referrer == "https://mailchimp.com"

    google_touchpoint = canonical_identity.touchpoints.filter(
        utm_source="google"
    ).first()
    assert google_touchpoint is not None
    assert google_touchpoint.utm_campaign == "brand_search"
    assert google_touchpoint.utm_term == "company name"
    assert google_touchpoint.ip_address == "192.168.1.100"

    touchpoint_timestamps = [tp.created_at for tp in merged_touchpoints]
    assert touchpoint_timestamps == sorted(touchpoint_timestamps)

    attribution_sources = [tp.utm_source for tp in merged_touchpoints if tp.utm_source]
    attribution_campaigns = [
        tp.utm_campaign for tp in merged_touchpoints if tp.utm_campaign
    ]

    assert "google" in attribution_sources
    assert "facebook" in attribution_sources
    assert "email" in attribution_sources

    assert "brand_search" in attribution_campaigns
    assert "retargeting_q4" in attribution_campaigns
    assert "weekly_digest" in attribution_campaigns

    touchpoint_urls = [tp.url for tp in merged_touchpoints]

    assert "home" in str(touchpoint_urls)
    assert "products" in str(touchpoint_urls)
    assert "landing" in str(touchpoint_urls)
    assert "pricing" in str(touchpoint_urls)
    assert "signup" in str(touchpoint_urls)

    for original_tp in original_canonical_touchpoints:
        current_tp = Touchpoint.objects.get(id=original_tp["id"])
        assert current_tp.identity == canonical_identity
        assert current_tp.url == original_tp["url"]
        assert current_tp.utm_source == original_tp["utm_source"]
        assert current_tp.created_at == original_tp["created_at"]

    for original_tp in original_source_touchpoints:
        current_tp = Touchpoint.objects.get(id=original_tp["id"])
        assert current_tp.identity == canonical_identity
        assert current_tp.url == original_tp["url"]
        assert current_tp.utm_source == original_tp["utm_source"]
        assert current_tp.created_at == original_tp["created_at"]

    continued_request = make_request(
        "/purchase", utm_params={"utm_source": "direct", "utm_medium": "bookmark"}
    )
    continued_request.user = user

    utm_parameter_middleware(continued_request)

    with patch.object(
        attribution_middleware.tracker,
        "get_identity_reference",
        return_value=str(source_identity.uuid),
    ):
        attribution_middleware(continued_request)

    assert canonical_identity.touchpoints.count() == 6

    latest_touchpoint = canonical_identity.touchpoints.latest("created_at")
    assert latest_touchpoint.utm_source == "direct"
    assert "/purchase" in latest_touchpoint.url

    assert source_identity.touchpoints.count() == 0


@pytest.mark.django_db
def test_shared_device_prevents_cross_user_attribution_contamination(
    attribution_middleware, utm_parameter_middleware, make_request
):
    user_a = User.objects.create_user(username="user_a", password="pass123")
    user_b = User.objects.create_user(username="user_b", password="pass456")

    user_a_identity = Identity.objects.create(linked_user=user_a)

    Touchpoint.objects.create(
        identity=user_a_identity,
        url="https://site.com/landing?utm_source=google&utm_campaign=expensive_ads",
        utm_source="google",
        utm_campaign="expensive_ads",
        utm_medium="cpc",
    )

    Touchpoint.objects.create(
        identity=user_a_identity,
        url="https://site.com/purchase",
        utm_source="",
        utm_medium="",
        utm_campaign="",
    )

    assert user_a_identity.touchpoints.count() == 2

    shared_device_request = make_request("/login")
    shared_device_request.user = user_b

    utm_parameter_middleware(shared_device_request)

    with patch.object(  # noqa: SIM117
        attribution_middleware.tracker,
        "get_identity_reference",
        return_value=str(user_a_identity.uuid),
    ):
        with patch.object(
            attribution_middleware.tracker, "set_identity_reference"
        ) as mock_set_cookie:
            with patch.object(
                attribution_middleware.tracker, "delete_cookie"
            ) as mock_delete_cookie:
                attribution_middleware(shared_device_request)

    assert shared_device_request.attribution.identity != user_a_identity
    assert shared_device_request.attribution.identity.linked_user == user_b

    user_b_identity = shared_device_request.attribution.identity
    assert user_b_identity.linked_user == user_b
    assert user_b_identity != user_a_identity

    mock_delete_cookie.assert_called_once()
    mock_set_cookie.assert_called_once()
    set_cookie_call = mock_set_cookie.call_args[0]
    assert set_cookie_call[1] == user_b_identity

    user_a_identity.refresh_from_db()
    assert user_a_identity.linked_user == user_a
    assert user_a_identity.touchpoints.count() == 2
    assert user_a_identity.touchpoints.filter(utm_campaign="expensive_ads").exists()

    assert user_b_identity.touchpoints.count() == 0

    assert Identity.objects.filter(linked_user=user_a).count() == 1
    assert Identity.objects.filter(linked_user=user_b).count() == 1
    assert Identity.objects.filter(linked_user=user_a).first() == user_a_identity
    assert Identity.objects.filter(linked_user=user_b).first() == user_b_identity

    user_b_browsing = make_request(
        "/products",
        utm_params={"utm_source": "facebook", "utm_campaign": "user_b_campaign"},
    )
    user_b_browsing.user = user_b

    utm_parameter_middleware(user_b_browsing)

    with patch.object(
        attribution_middleware.tracker,
        "get_identity_reference",
        return_value=str(user_b_identity.uuid),
    ):
        attribution_middleware(user_b_browsing)

    assert user_b_identity.touchpoints.count() == 1
    user_b_touchpoint = user_b_identity.touchpoints.first()
    assert user_b_touchpoint.utm_source == "facebook"
    assert user_b_touchpoint.utm_campaign == "user_b_campaign"

    assert user_a_identity.touchpoints.count() == 2

    assert not user_a_identity.touchpoints.filter(utm_source="facebook").exists()
    assert not user_b_identity.touchpoints.filter(utm_campaign="expensive_ads").exists()


@pytest.mark.django_db
def test_original_user_recovers_attribution_history_after_shared_device_conflict(
    attribution_middleware, utm_parameter_middleware, make_request
):
    user_a = User.objects.create_user(username="user_a", password="pass123")
    user_b = User.objects.create_user(username="user_b", password="pass456")

    user_a_original_identity = Identity.objects.create(linked_user=user_a)

    Touchpoint.objects.create(
        identity=user_a_original_identity,
        url="https://site.com/premium-landing?utm_source=google&utm_campaign=premium_ads&utm_term=expensive_keyword",
        utm_source="google",
        utm_campaign="premium_ads",
        utm_term="expensive_keyword",
        utm_medium="cpc",
    )

    Touchpoint.objects.create(
        identity=user_a_original_identity,
        url="https://site.com/high-value-page",
        utm_source="email",
        utm_campaign="vip_newsletter",
        utm_medium="newsletter",
    )

    Touchpoint.objects.create(
        identity=user_a_original_identity,
        url="https://site.com/expensive-conversion",
        utm_source="",
        utm_medium="",
        utm_campaign="",
    )

    assert user_a_original_identity.touchpoints.count() == 3

    user_b_request = make_request("/login")
    user_b_request.user = user_b

    utm_parameter_middleware(user_b_request)

    with patch.object(  # noqa: SIM117
        attribution_middleware.tracker,
        "get_identity_reference",
        return_value=str(user_a_original_identity.uuid),
    ):
        with patch.object(attribution_middleware.tracker, "set_identity_reference"):
            with patch.object(attribution_middleware.tracker, "delete_cookie"):
                attribution_middleware(user_b_request)

    user_b_identity = user_b_request.attribution.identity
    assert user_b_identity != user_a_original_identity
    assert user_b_identity.linked_user == user_b

    Touchpoint.objects.create(
        identity=user_b_identity,
        url="https://site.com/user-b-page?utm_source=facebook",
        utm_source="facebook",
        utm_campaign="user_b_campaign",
    )

    assert user_b_identity.touchpoints.count() == 1

    user_a_return_request = make_request("/login-return")
    user_a_return_request.user = user_a

    utm_parameter_middleware(user_a_return_request)

    with patch.object(  # noqa: SIM117
        attribution_middleware.tracker,
        "get_identity_reference",
        return_value=str(user_b_identity.uuid),
    ):
        with patch.object(
            attribution_middleware.tracker, "set_identity_reference"
        ) as mock_set_cookie:
            with patch.object(
                attribution_middleware.tracker, "delete_cookie"
            ) as mock_delete_cookie:
                attribution_middleware(user_a_return_request)

    returned_identity = user_a_return_request.attribution.identity
    assert returned_identity == user_a_original_identity
    assert returned_identity.linked_user == user_a

    assert returned_identity.touchpoints.count() == 3

    attribution_campaigns = list(
        returned_identity.touchpoints.values_list("utm_campaign", flat=True)
    )
    attribution_terms = list(
        returned_identity.touchpoints.values_list("utm_term", flat=True)
    )
    attribution_sources = list(
        returned_identity.touchpoints.values_list("utm_source", flat=True)
    )

    assert "premium_ads" in attribution_campaigns
    assert "vip_newsletter" in attribution_campaigns
    assert "expensive_keyword" in attribution_terms
    assert "google" in attribution_sources
    assert "email" in attribution_sources

    mock_delete_cookie.assert_called_once()
    mock_set_cookie.assert_called_once()
    set_cookie_call = mock_set_cookie.call_args[0]
    assert set_cookie_call[1] == user_a_original_identity

    user_b_identity.refresh_from_db()
    assert user_b_identity.linked_user == user_b
    assert user_b_identity.touchpoints.count() == 1
    assert user_b_identity.touchpoints.first().utm_source == "facebook"

    assert not user_a_original_identity.touchpoints.filter(
        utm_source="facebook"
    ).exists()
    assert not user_b_identity.touchpoints.filter(utm_campaign="premium_ads").exists()

    user_a_continued = make_request(
        "/continue-journey",
        utm_params={"utm_source": "returning_user", "utm_campaign": "welcome_back"},
    )
    user_a_continued.user = user_a

    utm_parameter_middleware(user_a_continued)

    with patch.object(
        attribution_middleware.tracker,
        "get_identity_reference",
        return_value=str(user_a_original_identity.uuid),
    ):
        attribution_middleware(user_a_continued)

    assert user_a_original_identity.touchpoints.count() == 4
    latest_touchpoint = user_a_original_identity.touchpoints.latest("created_at")
    assert latest_touchpoint.utm_source == "returning_user"
    assert latest_touchpoint.utm_campaign == "welcome_back"

    final_campaigns = list(
        user_a_original_identity.touchpoints.values_list("utm_campaign", flat=True)
    )
    assert "premium_ads" in final_campaigns
    assert "vip_newsletter" in final_campaigns
    assert "welcome_back" in final_campaigns

    assert user_a_original_identity.touchpoints.filter(
        utm_term="expensive_keyword"
    ).exists()
    assert user_a_original_identity.touchpoints.filter(
        url__contains="expensive-conversion"
    ).exists()
