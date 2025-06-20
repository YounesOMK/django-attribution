import functools
import logging

logger = logging.getLogger(__name__)

__all__ = [
    "conversion_events",
]


def conversion_events(*events: str):
    """
    Decorator to restrict which conversion events can be recorded in a view.

    Limits conversion recording to specified event types for the duration
    of the decorated view function.

    Args:
        *events: Allowed conversion event names

    Usage:
        @conversion_events('purchase', 'signup')
        def checkout_view(request):
            record_conversion(request, 'purchase', value=99.99)
    """

    allowed_events = set(events) if events else None

    def decorator(func):
        @functools.wraps(func)
        def wrapper(request, *args, **kwargs):
            # Set allowed conversion events directly on the request
            request._allowed_conversion_events = allowed_events

            try:
                response = func(request, *args, **kwargs)
            finally:
                # Clean up
                if hasattr(request, "_allowed_conversion_events"):
                    delattr(request, "_allowed_conversion_events")

            return response

        return wrapper

    return decorator
