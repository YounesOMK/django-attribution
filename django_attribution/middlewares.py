import logging
from typing import Dict, Optional
from urllib.parse import unquote_plus

from django.http import HttpResponse

from .conf import attribution_settings
from .mixins import RequestExclusionMixin
from .models import Identity, Touchpoint
from .trackers import CookieIdentityTracker
from .types import AttributionHttpRequest

logger = logging.getLogger(__name__)

__all__ = [
    "TrackingParameterMiddleware",
    "AttributionMiddleware",
]


class TrackingParameterMiddleware(RequestExclusionMixin):
    """
    Extracts and validates tracking parameters from incoming requests.

    This middleware processes UTM parameters and click tracking IDs from
    request URLs, validates and sanitizes the values, then stores them in
    request.META['tracking_params'] for use by AttributionMiddleware.

    Must be placed before AttributionMiddleware in MIDDLEWARE setting.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request: AttributionHttpRequest) -> HttpResponse:
        if self._should_skip_tracking_params_recording(request):
            return self.get_response(request)

        request.META["tracking_params"] = self._extract_tracking_parameters(request)

        response = self.get_response(request)

        return response

    def _extract_tracking_parameters(
        self, request: AttributionHttpRequest
    ) -> Dict[str, str]:
        tracking_params = {}
        for param in attribution_settings.TRACKING_PARAMETERS:
            value = request.GET.get(param, "").strip()
            if value:
                try:
                    validated = self._validate_utm_value(value, param)
                    if validated:
                        tracking_params[param] = validated
                except Exception as e:
                    logger.warning(f"Error extracting UTM parameter {param}: {e}")
        return tracking_params

    def _validate_utm_value(self, value: str, param_name: str) -> Optional[str]:
        try:
            decoded = unquote_plus(value)

            if len(decoded) > attribution_settings.MAX_UTM_LENGTH:
                logger.warning(f"UTM parameter {param_name} exceeds maximum length")
                return None

            cleaned = "".join(c for c in decoded if c.isprintable() or c.isspace())
            normalized = " ".join(cleaned.split())

            return normalized if normalized else None

        except Exception as e:
            logger.warning(f"Error processing UTM parameter {param_name}: {e}")
            return None


class AttributionMiddleware:
    """
    Core middleware that manages identity tracking and touchpoint creation.

    This middleware handles the attribution lifecycle on each request:
    - Retrieves or creates visitor identities based on tracking cookies
    - Resolves identity conflicts when anonymous users authenticate
    - Records touchpoints when visitors arrive with tracking parameters
    - Manages identity merging and reconciliation for authenticated users
    - Sets and maintains attribution tracking cookies

    Must be placed after TrackingParameterMiddleware in MIDDLEWARE setting.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.tracker = CookieIdentityTracker()

    def __call__(self, request: AttributionHttpRequest) -> HttpResponse:
        request.identity_tracker = self.tracker
        current_identity = self._get_current_identity_from_cookie(request)

        request.identity = (
            self._resolve_identity(request, current_identity)
            if self._should_resolve_identity(request, current_identity)
            else None
        )
        response = self.get_response(request)

        if request.identity:
            if self._has_tracking_data(request) and self._is_successful_response(
                response
            ):
                self._record_touchpoint(request.identity, request)
            self.tracker.apply_to_response(request, response)

        return response

    def _resolve_identity(
        self,
        request: "AttributionHttpRequest",
        current_identity: Optional[Identity],
    ) -> Identity:
        if request.user.is_authenticated:
            return self._resolve_authenticated_user_identity(request, current_identity)

        return self._resolve_anonymous_identity(request, current_identity)

    def _resolve_anonymous_identity(
        self,
        request: "AttributionHttpRequest",
        current_identity: Optional[Identity],
    ) -> Identity:
        if not current_identity:
            new_identity = Identity.objects.create(
                first_visit_user_agent=request.META.get("HTTP_USER_AGENT", ""),
            )
            self.tracker.set_identity(new_identity)
            logger.info(f"Created new anonymous identity {new_identity.uuid}")
            return new_identity

        canonical_identity = current_identity.get_canonical_identity()
        if canonical_identity != current_identity:
            self.tracker.set_identity(canonical_identity)
        else:
            self.tracker.refresh_identity(canonical_identity)

        return canonical_identity

    def _resolve_authenticated_user_identity(
        self,
        request: AttributionHttpRequest,
        current_identity: Optional[Identity],
    ) -> Identity:
        if not current_identity or current_identity.linked_user != request.user:
            logger.info(f"Reconciling identity for user {request.user.id}")
            return self._reconcile_user_identity(request)

        canonical = current_identity.get_canonical_identity()
        if canonical != current_identity:
            logger.debug(
                f"Using canonical identity "
                f"{canonical.uuid} instead of {current_identity.uuid}"
            )
            self.tracker.set_identity(canonical)

        return canonical

    def _get_current_identity_from_cookie(
        self, request: AttributionHttpRequest
    ) -> Optional[Identity]:
        identity_ref = self.tracker.get_identity_reference(request)
        if not identity_ref:
            return None

        try:
            return Identity.objects.get(uuid=identity_ref)
        except Identity.DoesNotExist:
            return None

    def _reconcile_user_identity(self, request: AttributionHttpRequest) -> Identity:
        from .reconciliation import reconcile_user_identity

        return reconcile_user_identity(request)

    def _has_tracking_data(self, request: AttributionHttpRequest) -> bool:
        tracking_params = request.META.get("tracking_params", {})
        return bool(tracking_params)

    def _is_successful_response(self, response: HttpResponse) -> bool:
        return response.status_code >= 200 and response.status_code < 300

    def _has_tracking_header(self, request: AttributionHttpRequest) -> bool:
        return bool(request.META.get(attribution_settings.ATTRIBUTION_TRIGGER_HEADER))

    def _has_attribution_trigger(self, request: AttributionHttpRequest) -> bool:
        return self._has_tracking_data(request) or self._has_tracking_header(request)

    def _should_resolve_identity(
        self,
        request: AttributionHttpRequest,
        current_identity: Optional[Identity],
    ) -> bool:
        return bool(current_identity) or self._has_attribution_trigger(request)

    def _record_touchpoint(
        self, identity: Identity, request: AttributionHttpRequest
    ) -> Touchpoint:
        tracking_params = request.META.get("tracking_params", {})

        return Touchpoint.objects.create(
            identity=identity,
            url=request.build_absolute_uri(),
            referrer=request.META.get("HTTP_REFERER", ""),
            utm_source=tracking_params.get("utm_source", ""),
            utm_medium=tracking_params.get("utm_medium", ""),
            utm_campaign=tracking_params.get("utm_campaign", ""),
            utm_term=tracking_params.get("utm_term", ""),
            utm_content=tracking_params.get("utm_content", ""),
            fbclid=tracking_params.get("fbclid", ""),
            gclid=tracking_params.get("gclid", ""),
            msclkid=tracking_params.get("msclkid", ""),
            ttclid=tracking_params.get("ttclid", ""),
            li_fat_id=tracking_params.get("li_fat_id", ""),
            twclid=tracking_params.get("twclid", ""),
            igshid=tracking_params.get("igshid", ""),
        )
