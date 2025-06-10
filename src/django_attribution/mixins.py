from django.http import HttpRequest

from .conf import django_attribution_settings


class RequestExclusionMixin:
    def _matches_url_patterns(self, request: HttpRequest, url_patterns: list) -> bool:
        return any(request.path.startswith(pattern) for pattern in url_patterns)

    def _is_bot_request(self, request: HttpRequest) -> bool:
        user_agent = request.META.get("HTTP_USER_AGENT", "").lower()
        return any(
            bot_pattern in user_agent
            for bot_pattern in django_attribution_settings.BOT_PATTERNS
        )

    def _should_skip_utm_params_recording(self, request: HttpRequest) -> bool:
        if self._matches_url_patterns(
            request, django_attribution_settings.UTM_EXCLUDED_URLS
        ):
            return True

        if django_attribution_settings.FILTER_BOTS and self._is_bot_request(request):
            return True

        return False
