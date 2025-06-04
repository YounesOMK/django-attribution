import logging
import uuid
from typing import Dict, Optional
from urllib.parse import unquote_plus

from django.http import HttpResponse

from .conf import django_attribution_settings
from .managers import AttributionManager
from .mixins import RequestExclusionMixin
from .models import Identity, Touchpoint
from .trackers import SessionIdentityTracker
from .types import AttributionHttpRequest

logger = logging.getLogger(__name__)


class UTMParameterMiddleware(RequestExclusionMixin):
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request: AttributionHttpRequest) -> HttpResponse:
        if self._is_excluded_request(request):
            return self.get_response(request)

        request.META["utm_params"] = self._extract_utm_parameters(request)

        response = self.get_response(request)

        return response

    def _extract_utm_parameters(
        self, request: AttributionHttpRequest
    ) -> Dict[str, str]:
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

    def _validate_utm_value(self, value: str, param_name: str) -> Optional[str]:
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
    ATTRIBUTION_SESSION_KEY = "_attribution_uuid"

    def __init__(self, get_response):
        self.get_response = get_response
        self.tracker = SessionIdentityTracker()

    def __call__(self, request: AttributionHttpRequest) -> HttpResponse:
        if self._is_excluded_request(request):
            return self.get_response(request)

        # Process request before view
        # Get or create attribution identity
        identity = self._get_or_create_identity(request)

        # Create touchpoint only if UTM params exist
        utm_params = request.META.get("utm_params", {})
        if utm_params:
            self._create_touchpoint(identity, request, utm_params)

        # TODO: Update identity.last_visit_at on every request or only with touchpoints?
        # For now, commenting this out - decide strategy later

        # Attach attribution manager to request
        request.attribution = AttributionManager(identity, request)

        # Call the view
        response = self.get_response(request)

        # Process response after view (if needed)
        return response

    def _get_or_create_identity(self, request: AttributionHttpRequest) -> Identity:
        """Get existing attribution identity or create new one"""
        # Try to get attribution UUID from session
        attribution_uuid = request.session.get(self.ATTRIBUTION_SESSION_KEY)

        if attribution_uuid:
            try:
                identity = Identity.objects.get(
                    uuid=attribution_uuid,
                    tracking_method=Identity.TrackingMethod.COOKIE,
                )
                # Check if this identity was merged - follow chain to canonical
                return identity.get_canonical_identity()
            except Identity.DoesNotExist:
                # Session had invalid UUID, create new one
                pass

        # Create new identity
        identity = Identity.objects.create(
            identity_value=str(uuid.uuid4()),
            tracking_method=Identity.TrackingMethod.COOKIE,
            first_ip_address=self._get_client_ip(request),
            first_user_agent=request.META.get("HTTP_USER_AGENT", ""),
        )

        # Store in session
        self.tracker.set_identity_reference(request, identity)

        return identity

    def _create_touchpoint(
        self, identity: Identity, request: AttributionHttpRequest, utm_params: dict
    ) -> Touchpoint:
        """Create a touchpoint for this identity with UTM parameters"""
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

    def _get_client_ip(self, request: AttributionHttpRequest) -> Optional[str]:
        """Extract client IP address from request"""
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            return x_forwarded_for.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR")
