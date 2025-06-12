from django.conf import settings

from .settings import (
    DEFAULT_ATTRIBUTION_COOKIE_DOMAIN,
    DEFAULT_ATTRIBUTION_COOKIE_HTTPONLY,
    DEFAULT_ATTRIBUTION_COOKIE_MAX_AGE,
    DEFAULT_ATTRIBUTION_COOKIE_NAME,
    DEFAULT_ATTRIBUTION_COOKIE_PATH,
    DEFAULT_ATTRIBUTION_COOKIE_SAMESITE,
    DEFAULT_ATTRIBUTION_COOKIE_SECURE,
    DEFAULT_ATTRIBUTION_TRIGGER_HEADER,
    DEFAULT_ATTRIBUTION_TRIGGER_VALUE,
    DEFAULT_BOT_PATTERNS,
    DEFAULT_DJANGO_ATTRIBUTION_CURRENCY,
    DEFAULT_FILTER_BOTS,
    DEFAULT_MAX_UTM_LENGTH,
    DEFAULT_UTM_PARAMETERS,
    DJANGO_ATTRIBUTION_UTM_EXCLUDED_URLS,
)


class DjangoAttributionSettings:
    @property
    def UTM_PARAMETERS(self):
        return getattr(
            settings,
            "DJANGO_ATTRIBUTION_UTM_PARAMETERS",
            DEFAULT_UTM_PARAMETERS,
        )

    @property
    def MAX_UTM_LENGTH(self):
        return getattr(
            settings,
            "DJANGO_ATTRIBUTION_MAX_UTM_LENGTH",
            DEFAULT_MAX_UTM_LENGTH,
        )

    @property
    def FILTER_BOTS(self):
        return getattr(
            settings,
            "DJANGO_ATTRIBUTION_FILTER_BOTS",
            DEFAULT_FILTER_BOTS,
        )

    @property
    def BOT_PATTERNS(self):
        return getattr(
            settings,
            "DJANGO_ATTRIBUTION_BOT_PATTERNS",
            DEFAULT_BOT_PATTERNS,
        )

    @property
    def CURRENCY(self):
        return getattr(
            settings,
            "DJANGO_ATTRIBUTION_CURRENCY",
            DEFAULT_DJANGO_ATTRIBUTION_CURRENCY,
        )

    @property
    def UTM_EXCLUDED_URLS(self):
        return getattr(
            settings,
            "DJANGO_ATTRIBUTION_UTM_EXCLUDED_URLS",
            DJANGO_ATTRIBUTION_UTM_EXCLUDED_URLS,
        )

    @property
    def COOKIE_NAME(self):
        return getattr(
            settings,
            "DJANGO_ATTRIBUTION_COOKIE_NAME",
            DEFAULT_ATTRIBUTION_COOKIE_NAME,
        )

    @property
    def COOKIE_MAX_AGE(self):
        return getattr(
            settings,
            "DJANGO_ATTRIBUTION_COOKIE_MAX_AGE",
            DEFAULT_ATTRIBUTION_COOKIE_MAX_AGE,
        )

    @property
    def COOKIE_DOMAIN(self):
        return getattr(
            settings,
            "DJANGO_ATTRIBUTION_COOKIE_DOMAIN",
            DEFAULT_ATTRIBUTION_COOKIE_DOMAIN,
        )

    @property
    def COOKIE_PATH(self):
        return getattr(
            settings,
            "DJANGO_ATTRIBUTION_COOKIE_PATH",
            DEFAULT_ATTRIBUTION_COOKIE_PATH,
        )

    @property
    def COOKIE_SECURE(self):
        return getattr(
            settings,
            "DJANGO_ATTRIBUTION_COOKIE_SECURE",
            DEFAULT_ATTRIBUTION_COOKIE_SECURE,
        )

    @property
    def COOKIE_HTTPONLY(self):
        return getattr(
            settings,
            "DJANGO_ATTRIBUTION_COOKIE_HTTPONLY",
            DEFAULT_ATTRIBUTION_COOKIE_HTTPONLY,
        )

    @property
    def COOKIE_SAMESITE(self):
        return getattr(
            settings,
            "DJANGO_ATTRIBUTION_COOKIE_SAMESITE",
            DEFAULT_ATTRIBUTION_COOKIE_SAMESITE,
        )

    @property
    def ATTRIBUTION_TRIGGER_HEADER(self):
        return getattr(
            settings,
            "DJANGO_ATTRIBUTION_TRIGGER_HEADER",
            DEFAULT_ATTRIBUTION_TRIGGER_HEADER,
        )

    @property
    def ATTRIBUTION_TRIGGER_VALUE(self):
        return getattr(
            settings,
            "DJANGO_ATTRIBUTION_TRIGGER_VALUE",
            DEFAULT_ATTRIBUTION_TRIGGER_VALUE,
        )


django_attribution_settings = DjangoAttributionSettings()
