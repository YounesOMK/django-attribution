import logging
import uuid
from typing import Optional

from django.http import HttpResponse

from .conf import attribution_settings
from .models import Identity
from .types import AttributionHttpRequest

logger = logging.getLogger(__name__)

__all__ = [
    "CookieIdentityTracker",
]


class CookieIdentityTracker:
    """
    Manages attribution identity tracking via HTTP cookies.

    Handles the storage and retrieval of identity references in browser
    cookies, enabling visitor recognition across sessions. Manages cookie
    lifecycle including creation, updates, and deletion while respecting
    configured security settings.

    The tracker queues cookie operations during request processing and
    applies them to the HTTP response.
    """

    def __init__(self):
        self._should_set_cookie = False
        self.cookie_name = attribution_settings.COOKIE_NAME
        self._pending_cookie_value = None
        self.delete_cookie_queued = False

    def get_identity_reference(self, request: AttributionHttpRequest) -> Optional[str]:
        cookie_value = request.COOKIES.get(self.cookie_name)

        if not cookie_value:
            return None

        try:
            uuid.UUID(cookie_value)
            return cookie_value
        except ValueError:
            logger.debug(f"Invalid UUID format in attribution cookie: {cookie_value}")
            return None

    def set_identity(self, identity: Identity) -> None:
        self._pending_cookie_value = str(identity.uuid)
        self._should_set_cookie = True
        logger.debug(f"Queued setting attribution cookie to: {identity.uuid}")

    def apply_to_response(
        self, request: AttributionHttpRequest, response: HttpResponse
    ) -> None:
        if self.delete_cookie_queued:
            self.delete_cookie(response)
            self.delete_cookie_queued = False

        if self._should_set_cookie and self._pending_cookie_value:
            self._set_attribution_cookie(request, response, self._pending_cookie_value)

        # Reset state
        self._pending_cookie_value = None
        self._should_set_cookie = False

    def _set_attribution_cookie(
        self, request: AttributionHttpRequest, response: HttpResponse, value: str
    ) -> None:
        cookie_kwargs = {
            "value": value,
            "max_age": attribution_settings.COOKIE_MAX_AGE,
            "path": attribution_settings.COOKIE_PATH,
            "httponly": attribution_settings.COOKIE_HTTPONLY,
            "samesite": attribution_settings.COOKIE_SAMESITE,
        }

        secure = attribution_settings.COOKIE_SECURE
        if secure is None:
            secure = request.is_secure()
        cookie_kwargs["secure"] = secure

        domain = attribution_settings.COOKIE_DOMAIN
        if domain:
            cookie_kwargs["domain"] = domain

        response.set_cookie(self.cookie_name, **cookie_kwargs)
        logger.debug(f"Set attribution cookie: {self.cookie_name}={value[:8]}...")

    def delete_cookie(self, response: HttpResponse) -> None:
        response.delete_cookie(
            self.cookie_name,
            path=attribution_settings.COOKIE_PATH,
            domain=attribution_settings.COOKIE_DOMAIN,
        )
        logger.debug(f"Deleted attribution cookie: {self.cookie_name}")

    def refresh_identity(self, identity: Identity) -> None:
        self.set_identity(identity)
