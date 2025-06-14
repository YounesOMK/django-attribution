from unittest.mock import patch

from django.http import HttpResponse

from django_attribution.conf import attribution_settings


def test_should_extract_all_standard_tracking_parameters(
    tracking_parameter_middleware, make_request
):
    tracking_params = {
        "utm_source": "google",
        "utm_medium": "cpc",
        "utm_campaign": "summer_sale",
        "utm_term": "running_shoes",
        "utm_content": "ad_variant_a",
    }
    request = make_request(tracking_params=tracking_params)

    tracking_parameter_middleware(request)

    assert request.META["tracking_params"] == tracking_params


def test_should_handle_missing_tracking_parameters_gracefully(
    tracking_parameter_middleware, make_request
):
    request = make_request(other_params={"other_param": "value"})

    tracking_parameter_middleware(request)

    assert request.META["tracking_params"] == {}


def test_should_extract_partial_tracking_parameters(
    tracking_parameter_middleware,
    make_request,
):
    """Should extract only the UTM parameters that are present"""
    tracking_params = {"utm_source": "facebook", "utm_campaign": "brand_awareness"}
    request = make_request(
        tracking_params=tracking_params, other_params={"other_param": "ignored"}
    )

    tracking_parameter_middleware(request)

    assert request.META["tracking_params"] == tracking_params


def test_should_ignore_empty_and_whitespace_only_parameters(
    tracking_parameter_middleware, make_request
):
    """Should not include UTM parameters that are empty or contain only whitespace"""
    tracking_params = {
        "utm_source": "google",
        "utm_medium": "",
        "utm_campaign": "   ",
        "utm_term": "\t\n",
        "utm_content": "valid_content",
        "fbclid": "1234567890",
    }
    request = make_request(tracking_params=tracking_params)

    tracking_parameter_middleware(request)

    expected_params = {
        "utm_source": "google",
        "utm_content": "valid_content",
        "fbclid": "1234567890",
    }
    assert request.META["tracking_params"] == expected_params


def test_should_url_decode_tracking_parameters(
    tracking_parameter_middleware,
    make_request,
):
    """Should properly decode URL-encoded UTM parameter values"""
    tracking_params = {
        "utm_source": "google%20ads",
        "utm_campaign": "summer%2Dsale%202024",
        "utm_content": "banner%20ad%20%2D%20top",
    }
    request = make_request(tracking_params=tracking_params)

    tracking_parameter_middleware(request)

    expected_params = {
        "utm_source": "google ads",
        "utm_campaign": "summer-sale 2024",
        "utm_content": "banner ad - top",
    }
    assert request.META["tracking_params"] == expected_params


def test_should_enforce_maximum_length_limit(
    tracking_parameter_middleware,
    make_request,
):
    """Should reject UTM parameters that exceed the maximum allowed length"""
    tracking_params = {
        "utm_source": "a" * 201,  # Exceeds MAX_UTM_LENGTH of 200
        "utm_medium": "a" * 100,
    }
    request = make_request(tracking_params=tracking_params)

    with patch("django_attribution.middlewares.logger") as mock_logger:
        tracking_parameter_middleware(request)

        mock_logger.warning.assert_called_with(
            "UTM parameter utm_source exceeds maximum length"
        )

    expected_params = {"utm_medium": "a" * 100}
    assert request.META["tracking_params"] == expected_params


def test_should_sanitize_non_printable_characters(
    tracking_parameter_middleware, make_request
):
    tracking_params = {
        "utm_source": "google\x00\x01ads",
        "utm_campaign": "summer\x7f\x80sale",
        "utm_content": "normal content",
    }
    request = make_request(tracking_params=tracking_params)

    tracking_parameter_middleware(request)

    expected_params = {
        "utm_source": "googleads",
        "utm_campaign": "summersale",
        "utm_content": "normal content",
    }
    assert request.META["tracking_params"] == expected_params


def test_should_normalize_whitespace(tracking_parameter_middleware, make_request):
    """Should normalize multiple whitespace characters to single spaces"""
    tracking_params = {
        "utm_source": "  google   ads  ",
        "utm_campaign": "summer\t\nsale\r\n2024",
        "utm_content": "banner\n\n\nad",
    }
    request = make_request(tracking_params=tracking_params)

    tracking_parameter_middleware(request)

    expected_params = {
        "utm_source": "google ads",
        "utm_campaign": "summer sale 2024",
        "utm_content": "banner ad",
    }
    assert request.META["tracking_params"] == expected_params


def test_should_handle_unicode_characters_properly(
    tracking_parameter_middleware, make_request
):
    """Should properly handle international characters in UTM parameters"""
    tracking_params = {
        "utm_source": "поисковик",  # Cyrillic
        "utm_campaign": "été_2024",  # French
        "utm_content": "夏季活动",  # Chinese
        "utm_term": "المؤتمر العربي الدولي للتعليم",
    }
    request = make_request(tracking_params=tracking_params)

    tracking_parameter_middleware(request)

    assert request.META["tracking_params"] == tracking_params


def test_should_process_case_sensitive_parameters(
    tracking_parameter_middleware, make_request
):
    """Should only extract parameters with exact case-sensitive names"""
    all_params = {
        "UTM_SOURCE": "google",  # Wrong case
        "utm_source": "facebook",  # Correct case
        "Utm_Medium": "cpc",  # Wrong case
        "utm_campaign": "summer",  # Correct case
    }
    request = make_request(other_params=all_params)

    tracking_parameter_middleware(request)

    expected_params = {"utm_source": "facebook", "utm_campaign": "summer"}
    assert request.META["tracking_params"] == expected_params


def test_should_not_interfere_with_other_request_processing(
    tracking_parameter_middleware, make_request
):
    request = make_request(tracking_params={"utm_source": "google"})
    original_get_params = dict(request.GET)

    result = tracking_parameter_middleware(request)

    assert isinstance(result, HttpResponse)
    assert dict(request.GET) == original_get_params
    assert "tracking_params" in request.META


def test_should_handle_extremely_long_parameter_lists(
    tracking_parameter_middleware, request_factory
):
    params = {f"param_{i}": f"value_{i}" for i in range(100)}
    params.update({"utm_source": "google", "utm_campaign": "test"})

    request = request_factory.get("/", params)

    tracking_parameter_middleware(request)

    expected_params = {"utm_source": "google", "utm_campaign": "test"}
    assert request.META["tracking_params"] == expected_params


def test_should_log_validation_errors_appropriately(
    tracking_parameter_middleware, make_request
):
    tracking_params = {
        "utm_source": "a" * 201,  # Too long
        "utm_medium": "valid",
    }
    request = make_request(tracking_params=tracking_params)

    with patch("django_attribution.middlewares.logger") as mock_logger:
        tracking_parameter_middleware(request)

        mock_logger.warning.assert_called_with(
            "UTM parameter utm_source exceeds maximum length"
        )


def test_should_be_defensive_against_unexpected_exceptions(
    tracking_parameter_middleware, make_request
):
    request = make_request(tracking_params={"utm_source": "test"})

    with patch.object(
        tracking_parameter_middleware,
        "_validate_utm_value",
    ) as mock_validate:
        mock_validate.side_effect = Exception("Unexpected error")

        with patch("django_attribution.middlewares.logger") as mock_logger:
            tracking_parameter_middleware(request)

            mock_logger.warning.assert_called()
            assert request.META["tracking_params"] == {}


def test_tracking_parameter_constants_should_include_all_standard_parameters(
    tracking_parameter_middleware,
):
    """Should define all five standard UTM parameters"""
    expected_params = {
        "utm_source",
        "utm_medium",
        "utm_campaign",
        "utm_term",
        "utm_content",
        "fbclid",
        "gclid",
        "msclkid",
        "ttclid",
        "li_fat_id",
        "twclid",
        "igshid",
    }
    assert set(attribution_settings.TRACKING_PARAMETERS) == set(expected_params)


def test_should_have_reasonable_maximum_length_limit(tracking_parameter_middleware):
    """Should define a reasonable maximum length for UTM parameters"""
    assert 50 <= attribution_settings.MAX_UTM_LENGTH <= 500


def test_should_ignore_requests_from_robots_and_crawlers(
    tracking_parameter_middleware, make_request
):
    tracking_params = {
        "utm_source": "google",
        "utm_medium": "cpc",
        "utm_campaign": "summer_sale",
    }

    bot_user_agents = [
        "Googlebot/2.1 (+http://www.google.com/bot.html)",
        "Mozilla/5.0 (compatible; Bingbot/2.0; +http://www.bing.com/bingbot.htm)",
        "facebookexternalhit/1.1 (+http://www.facebook.com/externalhit_uatext.php)",
        "Twitterbot/1.0",
        "LinkedInBot/1.0 (compatible; Mozilla/5.0; Apache-HttpClient +http://www.linkedin.com)",
        "Slackbot-LinkExpanding 1.0 (+https://api.slack.com/robots)",
        "Mozilla/5.0 (compatible; YandexBot/3.0; +http://yandex.com/bots)",
        "DuckDuckBot/1.0; (+http://duckduckgo.com/duckduckbot.html)",
        "Mozilla/5.0 (compatible; AhrefsBot/7.0; +http://ahrefs.com/robot/)",
        "SemrushBot/7~bl; +http://www.semrush.com/bot.html",
        "Mozilla/5.0 (compatible; MJ12bot/v1.4.8; http://mj12bot.com/)",
        "spider",
        "crawler",
        "scraper",
        "bot",
        "robot",
    ]

    for user_agent in bot_user_agents:
        request = make_request(tracking_params=tracking_params)
        request.META["HTTP_USER_AGENT"] = user_agent

        tracking_parameter_middleware(request)

        assert (
            request.META.get("tracking_params", {}) == {}
        ), f"Failed for user agent: {user_agent}"
