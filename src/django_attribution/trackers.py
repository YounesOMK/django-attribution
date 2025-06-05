import logging
import uuid
from abc import ABC, abstractmethod
from typing import Optional

from django.http import HttpRequest, HttpResponse

from .conf import django_attribution_settings
from .models import Identity

logger = logging.getLogger(__name__)


class IdentityTracker(ABC):
    @abstractmethod
    def get_identity_reference(self, request: HttpRequest) -> Optional[str]:
        """Get identity reference from request"""
        pass

    @abstractmethod
    def set_identity_reference(self, request: HttpRequest, identity: Identity) -> None:
        """Queue setting identity reference for response"""
        pass

    @abstractmethod
    def apply_to_response(self, request: HttpRequest, response: HttpResponse) -> None:
        """Apply any pending operations to the response"""
        pass


class CookieIdentityTracker(IdentityTracker):
    """Cookie-based attribution identity tracker"""

    def __init__(self):
        self.cookie_name = django_attribution_settings.COOKIE_NAME
        self._pending_cookie_value = None
        self._should_set_cookie = False

    def get_identity_reference(self, request: HttpRequest) -> Optional[str]:
        """Get attribution identity UUID from cookie"""
        cookie_value = request.COOKIES.get(self.cookie_name)

        if not cookie_value:
            return None

        # Validate UUID format
        try:
            uuid.UUID(cookie_value)
            return cookie_value
        except ValueError:
            logger.debug(f"Invalid UUID format in attribution cookie: {cookie_value}")
            return None

    def set_identity_reference(self, request: HttpRequest, identity: Identity) -> None:
        self._pending_cookie_value = str(identity.uuid)
        self._should_set_cookie = True
        logger.debug(f"Queued setting attribution cookie to: {identity.uuid}")

    def apply_to_response(self, request: HttpRequest, response: HttpResponse) -> None:
        if self._should_set_cookie and self._pending_cookie_value:
            self._set_attribution_cookie(request, response, self._pending_cookie_value)

        # Reset state
        self._pending_cookie_value = None
        self._should_set_cookie = False

    def _set_attribution_cookie(
        self, request: HttpRequest, response: HttpResponse, value: str
    ) -> None:
        cookie_kwargs = {
            "value": value,
            "max_age": django_attribution_settings.COOKIE_MAX_AGE,
            "path": django_attribution_settings.COOKIE_PATH,
            "httponly": django_attribution_settings.COOKIE_HTTPONLY,
            "samesite": django_attribution_settings.COOKIE_SAMESITE,
        }

        secure = django_attribution_settings.COOKIE_SECURE
        if secure is None:
            secure = request.is_secure()
        cookie_kwargs["secure"] = secure

        domain = django_attribution_settings.COOKIE_DOMAIN
        if domain:
            cookie_kwargs["domain"] = domain

        response.set_cookie(self.cookie_name, **cookie_kwargs)
        logger.debug(f"Set attribution cookie: {self.cookie_name}={value[:8]}...")

    def delete_cookie(self, response: HttpResponse) -> None:
        """Delete the attribution cookie (for GDPR compliance, etc.)"""
        response.delete_cookie(
            self.cookie_name,
            path=django_attribution_settings.COOKIE_PATH,
            domain=django_attribution_settings.COOKIE_DOMAIN,
        )
        logger.debug(f"Deleted attribution cookie: {self.cookie_name}")

    def refresh_identity(self, request: HttpRequest, identity: Identity) -> None:
        self.set_identity_reference(request, identity)
