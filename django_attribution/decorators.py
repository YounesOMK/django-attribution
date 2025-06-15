import functools
import logging
from typing import Optional, Set

from django.http import HttpResponse

from django_attribution.types import AttributionHttpRequest

logger = logging.getLogger(__name__)

__all__ = [
    "conversion_events",
    "ConversionEventsMixin",
]


def conversion_events(*events: str, require_identity: bool = True):
    allowed_events = set(events) if events else None

    def decorator(func):
        @functools.wraps(func)
        def wrapper(request, *args, **kwargs):
            request._allowed_conversion_events = allowed_events
            request._require_identity_for_conversions = require_identity

            try:
                response = func(request, *args, **kwargs)
            finally:
                # Clean up
                if hasattr(request, "_allowed_conversion_events"):
                    delattr(request, "_allowed_conversion_events")
                if hasattr(request, "_require_identity_for_conversions"):
                    delattr(request, "_require_identity_for_conversions")

            return response

        return wrapper

    return decorator


class ConversionEventsMixin:
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
