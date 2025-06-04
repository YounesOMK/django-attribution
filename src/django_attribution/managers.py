from .models import Identity
from .types import AttributionHttpRequest


class AttributionManager:
    def __init__(self, identity: Identity, request: AttributionHttpRequest):
        self.identity = identity
        self.request = request

    def track_conversion(self, event: str, **kwargs):
        """Track a conversion event - will be implemented next"""
        # TODO: Implement conversion tracking with attribution window (30 days for now)
        pass
