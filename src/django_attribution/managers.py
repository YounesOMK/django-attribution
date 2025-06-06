from typing import TYPE_CHECKING, Optional

from .models import Identity

if TYPE_CHECKING:
    from .trackers import CookieIdentityTracker
    from .types import AttributionHttpRequest


class AttributionManager:
    def __init__(
        self,
        identity: Optional[Identity],
        request: "AttributionHttpRequest",
        tracker: "CookieIdentityTracker",
    ):
        self.identity = identity
        self.tracker = tracker
        self.request = request

    def track_conversion(self, event: str, **kwargs):
        """Track a conversion event - will be implemented next"""
        # TODO: Implement conversion tracking with attribution window (30 days for now)
        pass
