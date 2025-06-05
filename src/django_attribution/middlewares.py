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
        if self._is_excluded_request(request):
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
    def __init__(self, get_response):
        self.get_response = get_response
        self.tracker = CookieIdentityTracker()

    def __call__(self, request: "AttributionHttpRequest") -> HttpResponse:
        if self._is_excluded_request(request):
            return self.get_response(request)

        try:
            identity = self._get_or_create_identity(request)

            utm_params = request.META.get("utm_params", {})
            if utm_params:
                self._create_touchpoint(identity, request, utm_params)

            request.attribution = AttributionManager(identity, request, self.tracker)

            response = self.get_response(request)

            self.tracker.apply_to_response(request, response)

            return response

        except Exception as e:
            logger.error(f"Attribution middleware error: {e}", exc_info=True)
            # Don't break the request if attribution fails
            response = self.get_response(request)
            return response

    def _get_or_create_identity(self, request: "AttributionHttpRequest") -> Identity:
        attribution_uuid = self.tracker.get_identity_reference(request)

        if attribution_uuid:
            try:
                identity = Identity.objects.get(
                    uuid=attribution_uuid,
                    tracking_method=Identity.TrackingMethod.COOKIE,
                )

                canonical_identity = identity.get_canonical_identity()

                if canonical_identity != identity:
                    self.tracker.set_identity_reference(request, canonical_identity)
                    logger.debug(
                        "Updated cookie to"
                        "canonical identity: {canonical_identity.uuid}"
                    )

                return canonical_identity

            except Identity.DoesNotExist:
                logger.debug(f"Identity not found for UUID: {attribution_uuid}")

        identity = Identity.objects.create(
            tracking_method=Identity.TrackingMethod.COOKIE,
        )

        self.tracker.set_identity_reference(request, identity)
        logger.debug(f"Created new attribution identity: {identity.uuid}")

        return identity

    def _create_touchpoint(
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
            ip_address=self._get_client_ip(request),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
        )

    def _get_client_ip(self, request: "AttributionHttpRequest") -> "Optional[str]":
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            return x_forwarded_for.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR")
