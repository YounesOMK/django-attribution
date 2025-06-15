from .conf import attribution_settings
from .types import AttributionHttpRequest

__all__ = [
    "RequestExclusionMixin",
]


class RequestExclusionMixin:
    def _matches_url_patterns(
        self, request: AttributionHttpRequest, url_patterns: list
    ) -> bool:
        return any(request.path.startswith(pattern) for pattern in url_patterns)

    def _is_bot_request(self, request: AttributionHttpRequest) -> bool:
        user_agent = request.META.get("HTTP_USER_AGENT", "").lower()
        return any(
            bot_pattern in user_agent
            for bot_pattern in attribution_settings.BOT_PATTERNS
        )

    def _should_skip_tracking_params_recording(
        self, request: AttributionHttpRequest
    ) -> bool:
        if self._matches_url_patterns(request, attribution_settings.UTM_EXCLUDED_URLS):
            return True

        if attribution_settings.FILTER_BOTS and self._is_bot_request(request):
            return True

        return False
