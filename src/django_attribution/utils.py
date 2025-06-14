from typing import Optional

from django_attribution.types import AttributionHttpRequest

__all__ = [
    "extract_client_ip",
]


def extract_client_ip(request: AttributionHttpRequest) -> Optional[str]:
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")
