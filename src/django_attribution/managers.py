from typing import TYPE_CHECKING, Optional

from .models import Identity

if TYPE_CHECKING:
    pass


class AttributionManager:
    def __init__(
        self,
        identity: Optional[Identity],
    ):
        self.identity = identity

    def track_conversion(self, event: str, **kwargs):
        """Track a conversion event - will be implemented next"""
        # TODO: Implement conversion tracking with attribution window (30 days for now)
        pass
