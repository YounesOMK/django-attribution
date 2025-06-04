from django.conf import settings

from .settings import (
    DEFAULT_BOT_PATTERNS,
    DEFAULT_DJANGO_ATTRIBUTION_CURRENCY,
    DEFAULT_EXCLUDED_URLS,
    DEFAULT_FILTER_BOTS,
    DEFAULT_LOG_VALIDATION_ERRORS,
    DEFAULT_MAX_UTM_LENGTH,
    DEFAULT_UTM_PARAMETERS,
    DEFAULT_WINDOW_DAYS,
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
    def LOG_VALIDATION_ERRORS(self):
        return getattr(
            settings,
            "DJANGO_ATTRIBUTION_LOG_VALIDATION_ERRORS",
            DEFAULT_LOG_VALIDATION_ERRORS,
        )

    @property
    def CURRENCY(self):
        return getattr(
            settings,
            "DJANGO_ATTRIBUTION_CURRENCY",
            DEFAULT_DJANGO_ATTRIBUTION_CURRENCY,
        )

    @property
    def EXCLUDED_URLS(self):
        return getattr(
            settings,
            "DJANGO_ATTRIBUTION_EXCLUDED_URLS",
            DEFAULT_EXCLUDED_URLS,
        )

    @property
    def WINDOW_DAYS(self):
        return getattr(
            settings,
            "DJANGO_ATTRIBUTION_WINDOW_DAYS",
            DEFAULT_WINDOW_DAYS,
        )


django_attribution_settings = DjangoAttributionSettings()
