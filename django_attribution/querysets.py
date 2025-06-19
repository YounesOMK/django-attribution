import logging
from typing import Any, Dict, Optional

from django.db import models

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

    def identified(self):
        return self.exclude(identity__isnull=True)

    def valid(self):
        return self.active().confirmed()

    def record(
        self,
        request,
        event: str,
        value: Optional[float] = None,
        currency: Optional[str] = None,
        is_confirmed: bool = True,
        source_object=None,
        custom_data: Optional[dict] = None,
    ):
        """
        Records a conversion event for the current request's identity.

        Creates a new Conversion instance with the specified event details.
        Validates that the event type is allowed (if conversion_events decorator
        or mixin was used) and that an identity exists when required.

        Args:
            request: Request containing the current identity
            event: Conversion event name (e.g., 'purchase', 'signup')
            value: Monetary value of the conversion
            currency: Currency code (defaults to settings default)
            is_confirmed: Whether the conversion is confirmed/valid
            source_object: Related Django model instance
            custom_data: Additional conversion metadata

        Returns:
            Created Conversion instance, or None if validation fails

        Raises:
            ValueError: If event is not in allowed_conversion_events list
        """

        django_request = getattr(request, "_request", request)

        allowed_events = getattr(
            django_request,
            "_allowed_conversion_events",
            None,
        )
        current_identity = django_request.identity

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

        conversion_data: Dict[str, Any] = {
            "identity": current_identity,
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
            f"Recorded conversion '{event}' "
            f"for identity {current_identity.uuid if current_identity else 'anonymous'}"
        )
        return conversion

    def with_attribution(
        self,
        model=None,
        window_days=30,
        source_windows=None,
    ):
        from django_attribution.attribution_models import last_touch

        if model is None:
            model = last_touch

        return model.apply(
            self,
            window_days=window_days,
            source_windows=source_windows,
        )
