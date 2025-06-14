import functools
import logging
from typing import Optional, Set, cast

from django.http import HttpRequest, HttpResponse

from django_attribution.types import AttributionHttpRequest

logger = logging.getLogger(__name__)


def _create_record_conversion_method(request: AttributionHttpRequest):
    allowed_events = getattr(request, "_allowed_conversion_events", None)

    def record_conversion(
        event_type: str,
        value: Optional[float] = None,
        currency: Optional[str] = None,
        confirmed: bool = True,
        source_object=None,
        custom_data: Optional[dict] = None,
    ):
        if allowed_events is not None and event_type not in allowed_events:
            logger.warning(
                f"Attempted to record conversion '{event_type}' "
                f"not declared in allowed events. "
                f"Allowed: {allowed_events}"
            )
            raise ValueError(
                f"Conversion event '{event_type}' not allowed. "
                f"Allowed events: {sorted(allowed_events)}"
            )

        if not hasattr(request, "identity") or not request.identity:
            logger.warning(
                f"Cannot record conversion '{event_type}': "
                f"no identity found on request"
            )
            return None

        from .models import Conversion

        conversion_data = {
            "identity": request.identity,
            "conversion_type": event_type,
            "is_confirmed": confirmed,
        }

        if value is not None:
            conversion_data["conversion_value"] = value

        if currency is not None:
            conversion_data["currency"] = currency

        if source_object is not None:
            from django.contrib.contenttypes.models import ContentType

            conversion_data["source_content_type"] = ContentType.objects.get_for_model(
                source_object
            )
            conversion_data["source_object_id"] = source_object.pk

        if custom_data:
            conversion_data["custom_data"] = custom_data

        conversion = Conversion.objects.create(**conversion_data)
        logger.info(
            f"Recorded conversion '{event_type}' "
            f"for identity {request.identity.uuid}"
        )
        return conversion

    return record_conversion


def conversion_events(*events: str):
    allowed_events = set(events) if events else None

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Detect if this is a method (first arg is self)
            #  or function (first arg is request)
            if (
                args
                and hasattr(args[0], "__class__")
                and not isinstance(args[0], HttpRequest)
            ):
                if len(args) < 2:
                    return func(*args, **kwargs)
                self = args[0]
                request = args[1]
                remaining_args = args[2:]
            else:
                if not args:
                    return func(*args, **kwargs)
                self = None
                request = args[0]
                remaining_args = args[1:]

            if not isinstance(request, HttpRequest):
                return func(*args, **kwargs)

            attr_request = cast(AttributionHttpRequest, request)

            attr_request._allowed_conversion_events = allowed_events

            original_record_conversion = getattr(
                attr_request, "record_conversion", None
            )
            attr_request.record_conversion = _create_record_conversion_method(
                attr_request
            )

            try:
                if self is not None:
                    response = func(self, request, *remaining_args, **kwargs)
                else:
                    response = func(request, *remaining_args, **kwargs)
            finally:
                if original_record_conversion:
                    attr_request.record_conversion = original_record_conversion
                else:
                    if hasattr(attr_request, "record_conversion"):
                        delattr(attr_request, "record_conversion")

                if hasattr(attr_request, "_allowed_conversion_events"):
                    delattr(attr_request, "_allowed_conversion_events")

            return response

        return wrapper

    return decorator


class ConversionEventsMixin:
    conversion_events: Optional[Set[str]] = None

    def dispatch(
        self, request: AttributionHttpRequest, *args, **kwargs
    ) -> HttpResponse:
        if self.conversion_events is not None:
            request._allowed_conversion_events = set(self.conversion_events)
        else:
            request._allowed_conversion_events = None

        original_record_conversion = getattr(request, "record_conversion", None)
        request.record_conversion = _create_record_conversion_method(request)

        try:
            response = super().dispatch(request, *args, **kwargs)  # type: ignore[misc]
        finally:
            if original_record_conversion:
                request.record_conversion = original_record_conversion
            else:
                if hasattr(request, "record_conversion"):
                    delattr(request, "record_conversion")

            if hasattr(request, "_allowed_conversion_events"):
                delattr(request, "_allowed_conversion_events")

        return response
