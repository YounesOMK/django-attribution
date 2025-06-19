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
            django_request = getattr(request, "_request", request)

            django_request._allowed_conversion_events = allowed_events

            try:
                response = func(request, *args, **kwargs)
            finally:
                # Clean up
                if hasattr(django_request, "_allowed_conversion_events"):
                    delattr(django_request, "_allowed_conversion_events")

            return response

        return wrapper

    return decorator
