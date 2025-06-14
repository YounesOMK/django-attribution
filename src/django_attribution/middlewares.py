import logging
from typing import Dict, Optional
from urllib.parse import unquote_plus

from django.http import HttpResponse

from django_attribution.utils import extract_client_ip

from .conf import attribution_settings
from .mixins import RequestExclusionMixin
from .models import Identity, Touchpoint
from .trackers import CookieIdentityTracker
from .types import AttributionHttpRequest

logger = logging.getLogger(__name__)

__all__ = [
    "UTMParameterMiddleware",
    "AttributionMiddleware",
]


class UTMParameterMiddleware(RequestExclusionMixin):
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
    def __init__(self, get_response):
        self.get_response = get_response
        self.tracker = CookieIdentityTracker()

    def __call__(self, request: "AttributionHttpRequest") -> HttpResponse:
        request.identity_tracker = self.tracker
        request.identity = (
            self._resolve_identity(request)
            if self._should_resolve_identity(request)
            else None
        )
        response = self.get_response(request)

        if request.identity:
            if self._has_attribution_trigger(request):
                self._record_touchpoint(request.identity, request)
            self.tracker.apply_to_response(request, response)

        return response

    def _resolve_identity(self, request: "AttributionHttpRequest") -> Identity:
        if request.user.is_authenticated:
            return self._resolve_authenticated_user_identity(request)

        return self._resolve_anonymous_identity(request)

    def _resolve_anonymous_identity(
        self, request: "AttributionHttpRequest"
    ) -> Identity:
        current_identity = self._get_current_identity_from_cookie(request)

        if not current_identity:
            new_identity = Identity.objects.create(
                ip_address=extract_client_ip(request),
                user_agent=request.META.get("HTTP_USER_AGENT", ""),
            )
            self.tracker.set_identity(new_identity)
            logger.info(f"Created new anonymous identity {new_identity.uuid}")
            return new_identity

        canonical_identity = current_identity.get_canonical_identity()
        if canonical_identity != current_identity:
            self.tracker.set_identity(canonical_identity)

        return canonical_identity

    def _resolve_authenticated_user_identity(
        self, request: AttributionHttpRequest
    ) -> Identity:
        current_identity = self._get_current_identity_from_cookie(request)

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

    def _has_attribution_trigger(self, request: AttributionHttpRequest) -> bool:
        has_tracking_params = bool(request.META.get("tracking_params", {}))
        has_tracking_header = (
            request.META.get(attribution_settings.ATTRIBUTION_TRIGGER_HEADER)
            == attribution_settings.ATTRIBUTION_TRIGGER_VALUE
        )
        return has_tracking_params or has_tracking_header

    def _should_resolve_identity(self, request: AttributionHttpRequest) -> bool:
        if not request.user.is_authenticated:
            return self._has_attribution_trigger(request)

        current_identity = self._get_current_identity_from_cookie(request)
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
