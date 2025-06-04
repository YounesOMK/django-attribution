import logging
from abc import ABC, abstractmethod
from typing import Optional

from django.http import HttpRequest

from .models import Identity

logger = logging.getLogger(__name__)


class IdentityTracker(ABC):
    @abstractmethod
    def get_identity_reference(self, request: HttpRequest) -> Optional[str]:
        pass

    @abstractmethod
    def set_identity_reference(self, request: HttpRequest, identity: Identity) -> None:
        pass

    @abstractmethod
    def update_identity_reference(
        self, request: HttpRequest, new_identity: Identity
    ) -> None:
        pass


class SessionIdentityTracker(IdentityTracker):
    ATTRIBUTION_SESSION_KEY = "_attribution_uuid"

    def get_identity_reference(self, request: HttpRequest) -> Optional[str]:
        return request.session.get(self.ATTRIBUTION_SESSION_KEY)

    def set_identity_reference(self, request: HttpRequest, identity: Identity) -> None:
        request.session[self.ATTRIBUTION_SESSION_KEY] = str(identity.uuid)

    def update_identity_reference(
        self, request: HttpRequest, new_identity: Identity
    ) -> None:
        request.session[self.ATTRIBUTION_SESSION_KEY] = str(new_identity.uuid)
