import logging
from typing import TYPE_CHECKING
from urllib.parse import unquote_plus

from django.http import HttpResponse

from .conf import django_attribution_settings
from .managers import AttributionManager
from .mixins import RequestExclusionMixin
from .models import Identity, Touchpoint
from .trackers import CookieIdentityTracker

if TYPE_CHECKING:
    from typing import Dict, Optional

    from .types import AttributionHttpRequest

logger = logging.getLogger(__name__)


class UTMParameterMiddleware(RequestExclusionMixin):
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request: "AttributionHttpRequest") -> HttpResponse:
        if self._is_excluded_for_utm(request):
            return self.get_response(request)

        request.META["utm_params"] = self._extract_utm_parameters(request)

        response = self.get_response(request)

        return response

    def _extract_utm_parameters(
        self, request: "AttributionHttpRequest"
    ) -> "Dict[str, str]":
        utm_params = {}
        for param in django_attribution_settings.UTM_PARAMETERS:
            value = request.GET.get(param, "").strip()
            if value:
                try:
                    validated = self._validate_utm_value(value, param)
                    if validated:
                        utm_params[param] = validated
                except Exception as e:
                    if django_attribution_settings.LOG_VALIDATION_ERRORS:
                        logger.warning(f"Error extracting UTM parameter {param}: {e}")
                    continue
        return utm_params

    def _validate_utm_value(self, value: str, param_name: str) -> "Optional[str]":
        try:
            decoded = unquote_plus(value)

            if len(decoded) > django_attribution_settings.MAX_UTM_LENGTH:
                if django_attribution_settings.LOG_VALIDATION_ERRORS:
                    logger.warning(f"UTM parameter {param_name} exceeds maximum length")
                return None

            cleaned = "".join(c for c in decoded if c.isprintable() or c.isspace())
            normalized = " ".join(cleaned.split())

            return normalized if normalized else None

        except Exception as e:
            if django_attribution_settings.LOG_VALIDATION_ERRORS:
                logger.warning(f"Error processing UTM parameter {param_name}: {e}")
            return None


class AttributionMiddleware(RequestExclusionMixin):
    TRACKING_METHOD = Identity.TrackingMethod.COOKIE

    def __init__(self, get_response):
        self.get_response = get_response
        self.tracker = CookieIdentityTracker()

    def __call__(self, request: "AttributionHttpRequest") -> HttpResponse:
        try:
            identity = self._resolve_identity(request)
            request.attribution = AttributionManager(identity, request, self.tracker)

            response = self.get_response(request)

            if identity:
                self.tracker.apply_to_response(request, response)

            return response

        except Exception as e:
            logger.error(f"Attribution middleware error: {e}", exc_info=True)
            response = self.get_response(request)
            return response

    def _resolve_identity(
        self, request: "AttributionHttpRequest"
    ) -> "Optional[Identity]":
        utm_params = request.META.get("utm_params", {})

        if self._is_excluded_for_attribution(request):
            identity = self._find_existing_identity(request)
        else:
            identity = self._resolve_trackable_identity(request, utm_params)

        return self._link_authenticated_user(request, identity)

    def _find_existing_identity(
        self, request: "AttributionHttpRequest"
    ) -> "Optional[Identity]":
        identity_uuid = self.tracker.get_identity_reference(request)
        return self._lookup_identity(identity_uuid) if identity_uuid else None

    def _resolve_trackable_identity(
        self, request: "AttributionHttpRequest", utm_params: dict
    ) -> "Optional[Identity]":
        if not self._should_track_identity(request, utm_params):
            return None

        identity = self._get_or_create_identity(request)
        if utm_params:
            self._record_touchpoint(identity, request, utm_params)
        return identity

    def _should_track_identity(
        self, request: "AttributionHttpRequest", utm_params: dict
    ) -> bool:
        return bool(utm_params or self.tracker.get_identity_reference(request))

    def _link_authenticated_user(
        self, request: "AttributionHttpRequest", identity: "Optional[Identity]"
    ) -> "Optional[Identity]":
        if request.user.is_authenticated and identity:
            from .reconciliation import resolve_user_identity

            return resolve_user_identity(request, identity, self.tracker)
        return identity

    def _lookup_identity(self, identity_uuid: str) -> "Optional[Identity]":
        try:
            identity = Identity.objects.get(
                uuid=identity_uuid,
                tracking_method=self.TRACKING_METHOD,
            )
            return identity.get_canonical_identity()
        except Identity.DoesNotExist:
            return None

    def _get_or_create_identity(self, request: "AttributionHttpRequest") -> Identity:
        identity_uuid = self.tracker.get_identity_reference(request)

        if identity_uuid:
            identity = self._lookup_identity(identity_uuid)
            if identity:
                return self._ensure_canonical_cookie(request, identity)
            else:
                logger.debug(f"Identity not found for UUID: {identity_uuid}")

        return self._create_identity(request)

    def _ensure_canonical_cookie(
        self, request: "AttributionHttpRequest", identity: Identity
    ) -> Identity:
        canonical = identity.get_canonical_identity()

        if canonical != identity:
            self.tracker.set_identity_reference(request, canonical)
            logger.debug(f"Updated cookie to canonical identity: {canonical.uuid}")

        return canonical

    def _create_identity(self, request: "AttributionHttpRequest") -> Identity:
        identity = Identity.objects.create(tracking_method=self.TRACKING_METHOD)
        self.tracker.set_identity_reference(request, identity)
        logger.debug(f"Created new attribution identity: {identity.uuid}")
        return identity

    def _record_touchpoint(
        self, identity: Identity, request: "AttributionHttpRequest", utm_params: dict
    ) -> Touchpoint:
        return Touchpoint.objects.create(
            identity=identity,
            url=request.build_absolute_uri(),
            referrer=request.META.get("HTTP_REFERER", ""),
            utm_source=utm_params.get("utm_source", ""),
            utm_medium=utm_params.get("utm_medium", ""),
            utm_campaign=utm_params.get("utm_campaign", ""),
            utm_term=utm_params.get("utm_term", ""),
            utm_content=utm_params.get("utm_content", ""),
            ip_address=self._extract_client_ip(request),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
        )

    def _extract_client_ip(self, request: "AttributionHttpRequest") -> "Optional[str]":
        """Extract client IP address from request headers"""
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            return x_forwarded_for.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR")
