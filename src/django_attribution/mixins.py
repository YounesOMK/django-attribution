from django.http import HttpRequest

from .conf import django_attribution_settings


class RequestExclusionMixin:
    def _is_excluded_url(self, request: HttpRequest) -> bool:
        return any(
            request.path.startswith(url)
            for url in django_attribution_settings.EXCLUDED_URLS
        )

    def _is_bot_request(self, request: HttpRequest) -> bool:
        user_agent = request.META.get("HTTP_USER_AGENT", "").lower()
        return any(
            bot_pattern in user_agent
            for bot_pattern in django_attribution_settings.BOT_PATTERNS
        )

    def _is_excluded_request(self, request: HttpRequest) -> bool:
        if self._is_excluded_url(request):
            return True

        if django_attribution_settings.FILTER_BOTS and self._is_bot_request(request):
            return True

        return False
