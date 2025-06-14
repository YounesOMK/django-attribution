from .models import Conversion
from .types import AttributionHttpRequest

__all__ = [
    "record_conversion",
]


def record_conversion(request: AttributionHttpRequest, event_type: str, **kwargs):
    return Conversion.objects.record(request, event_type, **kwargs)
