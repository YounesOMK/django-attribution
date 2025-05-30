import logging
from typing import Dict, Optional
from urllib.parse import unquote_plus

from django.http import HttpRequest
from django.utils.deprecation import MiddlewareMixin

from .conf import django_attribution_settings

logger = logging.getLogger(__name__)


class UTMParameterMiddleware(MiddlewareMixin):
    def process_request(self, request: HttpRequest) -> None:
        if django_attribution_settings.FILTER_BOTS and self._is_bot_request(request):
            return None
        request.META["utm_params"] = self._extract_utm_parameters(request)
        return None

    def _extract_utm_parameters(self, request: HttpRequest) -> Dict[str, str]:
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

    def _is_bot_request(self, request: HttpRequest) -> bool:
        user_agent = request.META.get("HTTP_USER_AGENT", "").lower()
        return any(
            bot_pattern in user_agent
            for bot_pattern in django_attribution_settings.BOT_PATTERNS
        )
