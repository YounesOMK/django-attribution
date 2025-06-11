# types.py
from typing import TYPE_CHECKING

from django.http import HttpRequest

if TYPE_CHECKING:
    from .trackers import CookieIdentityTracker


class AttributionHttpRequest(HttpRequest):
    identity_tracker: "CookieIdentityTracker"
