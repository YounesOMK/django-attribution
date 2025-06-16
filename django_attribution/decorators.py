import functools
import logging

logger = logging.getLogger(__name__)

__all__ = [
    "conversion_events",
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
