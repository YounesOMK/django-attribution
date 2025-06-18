from .models import Conversion
from .types import AttributionHttpRequest

__all__ = [
    "record_conversion",
]


def record_conversion(request: AttributionHttpRequest, event_type: str, **kwargs):
    """
    Shortcut for Conversion.objects.record() that creates a conversion
    for the current request's identity. All keyword arguments are passed
    through to the ConversionQuerySet.record method.

    Args:
        request: AttributionHttpRequest containing the current identity
        event_type: Name of the conversion event to record
        **kwargs: Additional arguments (value, currency, custom_data, etc.)

    Returns:
        Created Conversion instance, or None if validation fails

    Example:
        record_conversion(request, 'purchase', value=99.99, currency='USD')
    """

    return Conversion.objects.record(request, event_type, **kwargs)
