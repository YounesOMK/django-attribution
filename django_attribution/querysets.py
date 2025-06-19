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


class EventQuerySet(BaseQuerySet):
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
        name: str,
        monetary_value: Optional[float] = None,
        currency: Optional[str] = None,
        is_confirmed: bool = True,
        source_object=None,
        custom_data: Optional[dict] = None,
    ):
        """
        Records an event for the current request's identity.

        Creates a new Event instance with the specified event details.
        Validates that the event type is allowed (if events decorator
        or mixin was used) and that an identity exists when required.

        Args:
            request: Request containing the current identity
            name: Event name (e.g., 'purchase', 'signup')
            monetary_value: Monetary value of the event
            currency: Currency code (defaults to settings default)
            is_confirmed: Whether the event is confirmed/valid
            source_object: Related Django model instance
            custom_data: Additional event metadata

        Returns:
            Created Event instance, or None if validation fails

        Raises:
            ValueError: If event is not in allowed_events list
        """

        django_request = getattr(request, "_request", request)

        allowed_events = getattr(
            django_request,
            "_allowed_events",
            None,
        )
        current_identity = django_request.identity

        if allowed_events is not None and name not in allowed_events:
            logger.warning(
                f"Attempted to record event '{name}' "
                f"not declared in allowed events. "
                f"Allowed: {allowed_events}"
            )
            raise ValueError(
                f"Event '{name}' not allowed. "
                f"Allowed events: {sorted(allowed_events)}"
            )

        event_data: Dict[str, Any] = {
            "identity": current_identity,
            "name": name,
            "is_confirmed": is_confirmed,
        }

        if monetary_value is not None:
            event_data["monetary_value"] = monetary_value

        if currency is not None:
            event_data["currency"] = currency

        if source_object is not None:
            from django.contrib.contenttypes.models import ContentType

            event_data["source_content_type"] = ContentType.objects.get_for_model(
                source_object
            )
            event_data["source_object_id"] = source_object.pk

        if custom_data:
            event_data["custom_data"] = custom_data

        event = self.model(**event_data)
        event.save()

        logger.info(
            f"Recorded event '{name}' "
            f"for identity {current_identity.uuid if current_identity else 'anonymous'}"
        )
        return event

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
