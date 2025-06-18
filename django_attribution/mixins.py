from typing import Optional, Set

from django.http import HttpResponse

from .conf import attribution_settings
from .types import AttributionHttpRequest

__all__ = [
    "ConversionEventsMixin",
    "RequestExclusionMixin",
]


class ConversionEventsMixin:
    """
    Mixin for Django views to control which conversion events can be recorded.

    Restricts conversion recording to a predefined set of event types for
    the duration of the view execution. Optionally allows conversions to be
    recorded without requiring an identity (for anonymous conversions).

    Attributes:
        conversion_events: Set of allowed event names for this view
        require_identity: Whether an identity is required for conversions

    Usage:
        class CheckoutView(ConversionEventsMixin, View):
            conversion_events = ['purchase', 'add_to_cart']
            require_identity = True
    """

    conversion_events: Optional[Set[str]] = None
    require_identity: bool = True

    def dispatch(
        self,
        request: AttributionHttpRequest,
        *args,
        **kwargs,
    ) -> HttpResponse:
        if self.conversion_events is not None:
            request._allowed_conversion_events = set(self.conversion_events)
            request._require_identity_for_conversions = self.require_identity

        try:
            response = super().dispatch(request, *args, **kwargs)  # type: ignore[misc]
        finally:
            # Clean up
            if hasattr(request, "_allowed_conversion_events"):
                delattr(request, "_allowed_conversion_events")
            if hasattr(request, "_require_identity_for_conversions"):
                delattr(request, "_require_identity_for_conversions")

        return response


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
