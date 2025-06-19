from .models import Event
from .types import AttributionHttpRequest

__all__ = [
    "record_event",
]


def record_event(request: AttributionHttpRequest, name: str, **kwargs):
    """
    Shortcut for Event.objects.record() that creates a event
    for the current request's identity. All keyword arguments are passed
    through to the EventQuerySet.record method.

    Args:
        request: AttributionHttpRequest containing the current identity
        name: Name of the event to record
        **kwargs: Additional arguments (value, currency, custom_data, etc.)

    Returns:
        Created Event instance, or None if validation fails

    Example:
        record_event(request, 'purchase', value=99.99, currency='USD')
    """

    return Event.objects.record(request, name, **kwargs)
