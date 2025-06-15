import logging
from typing import Optional

from django.db import models

from .types import AttributionHttpRequest

logger = logging.getLogger(__name__)


class BaseQuerySet(models.QuerySet):
    def active(self):
        return self.filter(is_active=True)

    def inactive(self):
        return self.filter(is_active=False)

    def newest_first(self):
        return self.order_by("-created_at")

    def oldest_first(self):
        return self.order_by("created_at")


class IdentityQuerySet(BaseQuerySet):
    pass


class TouchpointQuerySet(BaseQuerySet):
    pass


class ConversionQuerySet(BaseQuerySet):
    def confirmed(self):
        return self.filter(is_confirmed=True)

    def unconfirmed(self):
        return self.filter(is_confirmed=False)

    def record(
        self,
        request: AttributionHttpRequest,
        event: str,
        value: Optional[float] = None,
        currency: Optional[str] = None,
        is_confirmed: bool = True,
        source_object=None,
        custom_data: Optional[dict] = None,
    ):
        allowed_events = getattr(request, "_allowed_conversion_events", None)
        if allowed_events is not None and event not in allowed_events:
            logger.warning(
                f"Attempted to record conversion '{event}' "
                f"not declared in allowed events. "
                f"Allowed: {allowed_events}"
            )
            raise ValueError(
                f"Conversion event '{event}' not allowed. "
                f"Allowed events: {sorted(allowed_events)}"
            )

        if not hasattr(request, "identity") or not request.identity:
            logger.warning(
                f"Cannot record conversion '{event}': " f"no identity found on request"
            )
            return None

        conversion_data = {
            "identity": request.identity,
            "event": event,
            "is_confirmed": is_confirmed,
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

        conversion = self.model(**conversion_data)
        conversion.save()

        logger.info(
            f"Recorded conversion '{event}' " f"for identity {request.identity.uuid}"
        )
        return conversion

    def with_attribution(self, model=None, window_days=30):
        from django_attribution.attribution_models import LastTouchAttributionModel

        if model is None:
            model = LastTouchAttributionModel()

        return model.apply(self, window_days=window_days)
