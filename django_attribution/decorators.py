import functools
import logging

logger = logging.getLogger(__name__)

__all__ = [
    "conversion_events",
]


def conversion_events(*events: str, require_identity: bool = True):
    """
    Decorator to restrict which conversion events can be recorded in a view.

    Limits conversion recording to specified event types for the duration
    of the decorated view function.

    Args:
        *events: Allowed conversion event names
        require_identity: Whether identity is required for conversions

    Usage:
        @conversion_events('purchase', 'signup', require_identity=True)
        def checkout_view(request):
            record_conversion(request, 'purchase', value=99.99)
    """

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
