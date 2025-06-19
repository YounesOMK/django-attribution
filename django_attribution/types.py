# types.py
from typing import TYPE_CHECKING, Optional, Set

from django.http import HttpRequest

__all__ = [
    "AttributionHttpRequest",
]

if TYPE_CHECKING:
    from .models import Identity
    from .trackers import CookieIdentityTracker


class AttributionHttpRequest(HttpRequest):
    identity_tracker: "CookieIdentityTracker"
    identity: Optional["Identity"]
    _allowed_conversion_events: Optional[Set[str]]
