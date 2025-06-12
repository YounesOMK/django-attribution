# types.py
from typing import TYPE_CHECKING, Optional

from django.http import HttpRequest

if TYPE_CHECKING:
    from .models import Identity
    from .trackers import CookieIdentityTracker


class AttributionHttpRequest(HttpRequest):
    identity_tracker: "CookieIdentityTracker"
    identity: Optional["Identity"]
