import logging
from typing import TYPE_CHECKING, Optional
from urllib.parse import unquote_plus

from django.http import HttpResponse

from .conf import django_attribution_settings
from .managers import AttributionManager
from .mixins import RequestExclusionMixin
from .models import Identity, Touchpoint
from .trackers import CookieIdentityTracker

if TYPE_CHECKING:
    from typing import Dict

    from .types import AttributionHttpRequest

logger = logging.getLogger(__name__)


class UTMParameterMiddleware(RequestExclusionMixin):
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request: "AttributionHttpRequest") -> HttpResponse:
        if self._should_skip_utm_params_recording(request):
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


class AttributionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.tracker = CookieIdentityTracker()

    def __call__(self, request: "AttributionHttpRequest") -> HttpResponse:
        identity = None
        utm_params = request.META.get("utm_params", {})

        request.attribution = AttributionManager(
            identity=identity,
            tracker=self.tracker,
        )

        identity = self._resolve_identity(request)

        if utm_params:
            self._record_touchpoint(identity, request)

        if not identity:
            return self.get_response(request)

        response = self.get_response(request)

        self.tracker.apply_to_response(request, response)

        return response

    def _resolve_identity(
        self, request: "AttributionHttpRequest"
    ) -> Optional[Identity]:
        if request.user.is_authenticated:
            return self._resolve_authenticated_user_identity(request)

        return self._resolve_anonymous_identity(request)

    def _resolve_anonymous_identity(
        self, request: "AttributionHttpRequest"
    ) -> Optional[Identity]:
        utm_params = request.META.get("utm_params", {})

        if not utm_params:
            return None

        current_identity = self._get_current_identity_from_cookie(request)

        if not current_identity:
            current_identity = Identity.objects.create()
            assert current_identity is not None
            self.tracker.set_identity(current_identity)
            logger.debug(
                f"Created new identity {current_identity.uuid} for anonymous user"
            )

        if current_identity.linked_user:
            return None
        canonical_identity = current_identity.get_canonical_identity()
        if canonical_identity != current_identity:
            self.tracker.set_identity(canonical_identity)
            current_identity = canonical_identity

        return current_identity

    def _resolve_authenticated_user_identity(
        self, request: "AttributionHttpRequest"
    ) -> Optional[Identity]:
        current_identity = self._get_current_identity_from_cookie(request)

        if not current_identity:
            logger.debug(
                f"No current identity for"
                f" authenticated user {request.user.id}, resolving"
            )
            return self._reconcile_user_identity(request)

        if current_identity.linked_user != request.user:
            logger.debug(
                f"Current identity {current_identity.uuid} doesn't match "
                f"authenticated user {request.user.id}, resolving"
            )
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
        self, request: "AttributionHttpRequest"
    ) -> Optional[Identity]:
        identity_ref = self.tracker.get_identity_reference(request)
        if not identity_ref:
            return None

        try:
            return Identity.objects.get(uuid=identity_ref)
        except Identity.DoesNotExist:
            return None

    def _reconcile_user_identity(
        self, request: "AttributionHttpRequest"
    ) -> Optional[Identity]:
        from .reconciliation import reconcile_user_identity

        return reconcile_user_identity(request)

    def _record_touchpoint(
        self, identity: Optional[Identity], request: "AttributionHttpRequest"
    ) -> Touchpoint:
        utm_params = request.META.get("utm_params", {})
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
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            return x_forwarded_for.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR")
